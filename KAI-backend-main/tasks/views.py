from rest_framework import viewsets, views, status, generics
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q, Count
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.conf import settings

from core.services import write_audit
from core.permissions import HasPermissionKey
from core.permissions_catalog import TEAM_MANAGE, TASK_CREATE
from .models import Task, Comment, Attachment, Team, TaskLink, Sprint, BacklogItem
from .serializers import (
    TaskCardSerializer, TaskDetailSerializer, TaskCreateSerializer,
    CommentSerializer, AttachmentSerializer, TeamSerializer, TeamDetailSerializer,
    SprintSerializer, BacklogItemSerializer,
)
from .services import TaskService

User = get_user_model()

COLUMNS = ['todo', 'in_progress', 'blocked', 'review', 'done']


class CommentPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50


def _base_queryset():
    return (Task.objects
            .select_related('assignee', 'team', 'sprint', 'linked_bid', 'linked_bid__opportunity')
            .annotate(comment_count=Count('comments', distinct=True),
                      attachment_count=Count('attachments', distinct=True)))


class TaskFilterOptionsView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        assignees = User.objects.filter(user_type__in=['Admin', 'Manager', 'Employee']) \
            .order_by('first_name', 'email')
        teams = Team.objects.filter(is_active=True)
        # distinct labels across tasks
        labels = set()
        for arr in Task.objects.values_list('labels', flat=True):
            labels.update(arr or [])
        from .serializers import UserMiniSerializer
        return Response({
            'assignees': UserMiniSerializer(assignees, many=True).data,
            'teams': TeamSerializer(teams, many=True).data,
            'labels': sorted(labels),
            'priorities': [c[0] for c in Task.PRIORITY],
            'types': [c[0] for c in Task.TYPE_CHOICES],
        })


class TaskAssigneeCountsView(views.APIView):
    """Returns active (non-done) task counts per assignee: { "<user_id>": count }"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        counts = (
            Task.objects
            .exclude(status='done')
            .filter(assignee__isnull=False)
            .values('assignee_id')
            .annotate(count=Count('id'))
        )
        return Response({str(item['assignee_id']): item['count'] for item in counts})


class TaskBoardView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = _base_queryset()
        p = request.query_params

        view_mode = p.get('view', 'all')
        if view_mode == 'mine':
            qs = qs.filter(assignee=request.user)
        elif view_mode == 'team':
            qs = qs.filter(team__members=request.user)

        if p.get('search'):
            s = p['search']
            qs = qs.filter(Q(title__icontains=s) | Q(key__icontains=s) | Q(description__icontains=s))
        if p.getlist('assignee_id'):
            qs = qs.filter(assignee_id__in=p.getlist('assignee_id'))
        if p.get('team_id'):
            qs = qs.filter(team_id=p['team_id'])
        if p.getlist('priority'):
            qs = qs.filter(priority__in=p.getlist('priority'))
        if p.get('label'):
            qs = qs.filter(labels__contains=[p['label']])
        if p.get('task_type'):
            qs = qs.filter(task_type=p['task_type'])
        if p.get('linked_bid_id'):
            qs = qs.filter(linked_bid_id=p['linked_bid_id'])
        if p.get('due_from'):
            qs = qs.filter(due_date__gte=p['due_from'])
        if p.get('due_to'):
            qs = qs.filter(due_date__lte=p['due_to'])
        if p.get('overdue') == 'true':
            qs = qs.filter(due_date__lt=timezone.now()).exclude(status='done')
        if p.get('sprint_id'):
            sid = p['sprint_id']
            if sid == 'active':
                qs = qs.filter(sprint__status='active')
            elif sid == 'backlog':
                qs = qs.filter(sprint__isnull=True)
            else:
                qs = qs.filter(sprint_id=sid)
        if p.get('include_templates') != 'true':
            qs = qs.filter(is_recurrence_template=False)

        qs = qs.order_by('position', '-created_at')
        board = {}
        for col in COLUMNS:
            board[col] = TaskCardSerializer(
                [t for t in qs if t.status == col], many=True, context={'request': request}
            ).data
        return Response(board)


class TaskViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_queryset(self):
        return _base_queryset().prefetch_related(
            'comments__author', 'attachments__uploaded_by', 'outgoing_links__target_task'
        )

    def get_serializer_class(self):
        if self.action == 'create':
            return TaskCreateSerializer
        return TaskDetailSerializer

    def create(self, request, *args, **kwargs):
        ser = TaskCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        # status: employees can only create into todo
        requested_status = data.pop('status', 'todo')
        if requested_status not in ('todo', 'in_progress') or not request.user.has_perm_key('task.transition_any'):
            requested_status = 'todo'
        linked_bid_id = data.pop('linked_bid_id', None)
        recurrence_type = data.get('recurrence_type', 'none')
        top = Task.objects.filter(status=requested_status).order_by('position').first()
        position = (top.position - 1) if top else 0
        task = Task(reporter=request.user, created_by=request.user,
                    status=requested_status, position=position,
                    is_recurrence_template=(recurrence_type != 'none'), **data)
        if linked_bid_id:
            task.linked_bid_id = linked_bid_id
        task.save()
        write_audit(actor=request.user, model_name='Task', object_id=task.id,
                    action='created', new_state=task.status, request=request)
        out = TaskDetailSerializer(task, context={'request': request})
        return Response(out.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        ser = TaskDetailSerializer(instance, data=request.data, partial=partial,
                                   context={'request': request})
        ser.is_valid(raise_exception=True)
        # status is read-only here; handle linked_bid_id and sprint_id explicitly
        linked_bid_id = ser.validated_data.pop('linked_bid_id', 'unset')
        sprint_id = ser.validated_data.pop('sprint_id', 'unset')
        prev_assignee = instance.assignee_id
        ser.save()
        update_fields = []
        if linked_bid_id != 'unset':
            instance.linked_bid_id = linked_bid_id
            update_fields.append('linked_bid')
        if sprint_id != 'unset':
            instance.sprint_id = sprint_id
            update_fields.append('sprint')
        if update_fields:
            instance.save(update_fields=update_fields)
        # notify on (re)assignment
        if 'assignee' in ser.validated_data and instance.assignee_id and instance.assignee_id != prev_assignee:
            from notifications.services import notify
            notify(user=instance.assignee, kind='task_assigned',
                   title=f"You were assigned {instance.key}",
                   body=instance.title, link=f"/tasks?task={instance.id}",
                   actor=request.user)
        return Response(TaskDetailSerializer(instance, context={'request': request}).data)

    def destroy(self, request, *args, **kwargs):
        task = self.get_object()
        TaskService.delete(task, request.user, request=request)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def transition(self, request, pk=None):
        task = self.get_object()
        result = TaskService.transition(
            task.id, request.user,
            action=request.data.get('action'),
            target=request.data.get('target'),
            reason=request.data.get('reason'),
            request=request,
        )
        return Response(TaskDetailSerializer(result, context={'request': request}).data)

    @action(detail=True, methods=['post'])
    def reorder(self, request, pk=None):
        task = self.get_object()
        result = TaskService.reorder(
            task.id, request.user,
            before_id=request.data.get('before_id'),
            after_id=request.data.get('after_id'),
            status=request.data.get('status'),
        )
        return Response(TaskCardSerializer(result, context={'request': request}).data)

    # ---- comments ----
    @action(detail=True, methods=['get', 'post'], url_path='comments')
    def task_comments(self, request, pk=None):
        task = self.get_object()
        if request.method == 'POST':
            body = (request.data.get('body') or '').strip()
            if not body:
                return Response({'body': ['Comment cannot be empty.']}, status=400)
            c = Comment.objects.create(task=task, author=request.user, body=body)
            return Response(CommentSerializer(c).data, status=201)
            
        comments = task.comments.all()
        paginator = CommentPagination()
        page = paginator.paginate_queryset(comments, request)
        if page is not None:
            return paginator.get_paginated_response(CommentSerializer(page, many=True, context={'request': request}).data)
        return Response(CommentSerializer(comments, many=True, context={'request': request}).data)

    @action(detail=True, methods=['patch', 'delete'], url_path='comments/(?P<cid>[^/.]+)')
    def comment_detail(self, request, pk=None, cid=None):
        task = self.get_object()
        comment = get_object_or_404(Comment, id=cid, task=task)
        if request.method == 'DELETE':
            if not (request.user.user_type == 'Admin' or request.user.has_perm_key('task.manage_comments') or comment.author_id == request.user.id):
                return Response({'detail': 'Not allowed.'}, status=403)
            comment.delete()
            return Response(status=204)
        # PATCH
        if not (request.user.user_type == 'Admin' or request.user.has_perm_key('task.manage_comments') or comment.author_id == request.user.id):
            return Response({'detail': 'Not allowed.'}, status=403)
        body = (request.data.get('body') or '').strip()
        if not body:
            return Response({'body': ['Comment cannot be empty.']}, status=400)
        comment.body = body
        comment.is_edited = True
        comment.save(update_fields=['body', 'is_edited', 'updated_at'])
        return Response(CommentSerializer(comment).data)

    # ---- attachments ----
    @action(detail=True, methods=['post'], url_path='attachments',
            parser_classes=[MultiPartParser, FormParser, JSONParser])
    def add_attachment(self, request, pk=None):
        task = self.get_object()
        f = request.FILES.get('file')
        url = request.data.get('url', '').strip()
        link_label = request.data.get('link_label', '').strip()

        if f:
            if f.size > settings.MAX_ATTACHMENT_SIZE:
                return Response({'file': ['File too large.']}, status=400)
            att = Attachment.objects.create(
                task=task, file=f, filename=f.name, size=f.size,
                content_type=getattr(f, 'content_type', ''), uploaded_by=request.user,
            )
        elif url:
            att = Attachment.objects.create(
                task=task, url=url, link_label=link_label,
                filename=link_label or url, size=0, uploaded_by=request.user,
            )
        else:
            return Response({'detail': 'Provide a file or a URL.'}, status=400)

        return Response(AttachmentSerializer(att, context={'request': request}).data, status=201)

    @action(detail=True, methods=['delete'], url_path='attachments/(?P<aid>[^/.]+)')
    def delete_attachment(self, request, pk=None, aid=None):
        task = self.get_object()
        att = get_object_or_404(Attachment, id=aid, task=task)
        if not (request.user.user_type == 'Admin' or request.user.has_perm_key('task.manage_tasks')
                or att.uploaded_by_id == request.user.id or task.reporter_id == request.user.id):
            return Response({'detail': 'Not allowed.'}, status=403)
        if att.file:
            att.file.delete(save=False)
        att.delete()
        return Response(status=204)

    # ---- links ----
    @action(detail=True, methods=['post'], url_path='links')
    def add_link(self, request, pk=None):
        task = self.get_object()
        relation = request.data.get('relation')
        target_id = request.data.get('target_task_id')
        if relation not in dict(TaskLink.RELATION):
            return Response({'relation': ['Invalid relation.']}, status=400)
        TaskService.add_link(task, request.user, relation, int(target_id), request=request)
        return Response(TaskDetailSerializer(task, context={'request': request}).data, status=201)

    @action(detail=True, methods=['delete'], url_path='links/(?P<link_id>[^/.]+)')
    def delete_link(self, request, pk=None, link_id=None):
        task = self.get_object()
        link = get_object_or_404(TaskLink, id=link_id, source_task=task)
        # remove mirror too
        TaskLink.objects.filter(source_task=link.target_task, target_task=task).delete()
        link.delete()
        return Response(status=204)


class BacklogView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = _base_queryset().filter(sprint__isnull=True)
        p = request.query_params
        if p.get('search'):
            s = p['search']
            qs = qs.filter(Q(title__icontains=s) | Q(key__icontains=s))
        if p.get('assignee_id'):
            qs = qs.filter(assignee_id=p['assignee_id'])
        qs = qs.order_by('position', '-created_at')
        return Response(TaskCardSerializer(qs, many=True, context={'request': request}).data)


class SprintViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = SprintSerializer
    pagination_class = None

    def get_queryset(self):
        return Sprint.objects.select_related('team').prefetch_related('tasks')

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        sprint = self.get_object()
        if sprint.status != 'planning':
            return Response({'detail': 'Only planning sprints can be started.'}, status=400)
        # Enforce one active sprint at a time
        if Sprint.objects.filter(status='active').exclude(pk=sprint.pk).exists():
            return Response({'detail': 'Another sprint is already active. Complete it first.'}, status=400)
        sprint.status = 'active'
        if not sprint.start_date:
            sprint.start_date = timezone.now().date()
        sprint.save()
        write_audit(actor=request.user, model_name='Sprint', object_id=sprint.id,
                    action='started', new_state='active', request=request)
        return Response(SprintSerializer(sprint, context={'request': request}).data)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        sprint = self.get_object()
        if sprint.status != 'active':
            return Response({'detail': 'Only active sprints can be completed.'}, status=400)
        # Move incomplete tasks to backlog
        sprint.tasks.exclude(status='done').update(sprint=None)
        sprint.status = 'completed'
        if not sprint.end_date:
            sprint.end_date = timezone.now().date()
        sprint.save()
        write_audit(actor=request.user, model_name='Sprint', object_id=sprint.id,
                    action='completed', new_state='completed', request=request)
        return Response(SprintSerializer(sprint, context={'request': request}).data)


class TeamViewSet(viewsets.ModelViewSet):
    pagination_class = None
    queryset = Team.objects.all().select_related('lead').prefetch_related('members')

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated()]
        return [HasPermissionKey.of(TEAM_MANAGE)()]

    def get_serializer_class(self):
        return TeamDetailSerializer if self.action == 'retrieve' else TeamSerializer

    @action(detail=True, methods=['post'], url_path='members')
    def add_members(self, request, pk=None):
        team = self.get_object()
        ids = request.data.get('user_ids', [])
        team.members.add(*User.objects.filter(id__in=ids))
        return Response(TeamDetailSerializer(team).data)

    @action(detail=True, methods=['delete'], url_path='members/(?P<user_id>[^/.]+)')
    def remove_member(self, request, pk=None, user_id=None):
        team = self.get_object()
        team.members.remove(user_id)
        return Response(status=204)


class PersonalBacklogItemViewSet(viewsets.ModelViewSet):
    """Private backlog — always scoped to request.user."""
    permission_classes = [IsAuthenticated]
    serializer_class = BacklogItemSerializer
    pagination_class = None
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        return BacklogItem.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def promote(self, request, pk=None):
        item = self.get_object()
        task = Task(
            title=item.title,
            description=item.notes,
            reporter=request.user,
            created_by=request.user,
        )
        task.save()
        write_audit(actor=request.user, model_name='Task', object_id=task.id,
                    action='promoted_from_backlog', request=request)
        item.delete()
        return Response(TaskCardSerializer(task, context={'request': request}).data,
                        status=status.HTTP_201_CREATED)
