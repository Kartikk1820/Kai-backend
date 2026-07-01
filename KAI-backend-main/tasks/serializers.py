from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import Task, Comment, Attachment, TaskLink, Team, Sprint, BacklogItem

User = get_user_model()


class UserMiniSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    avatar_initials = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'full_name', 'avatar_initials', 'email']


class TeamSerializer(serializers.ModelSerializer):
    member_count = serializers.SerializerMethodField()
    lead = UserMiniSerializer(read_only=True)
    lead_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='lead', write_only=True, required=False, allow_null=True)

    class Meta:
        model = Team
        fields = ['id', 'name', 'description', 'lead', 'lead_id', 'member_count', 'is_active']

    def get_member_count(self, obj):
        return obj.members.count()


class TeamDetailSerializer(TeamSerializer):
    members = UserMiniSerializer(many=True, read_only=True)

    class Meta(TeamSerializer.Meta):
        fields = TeamSerializer.Meta.fields + ['members']


class SprintSerializer(serializers.ModelSerializer):
    task_count = serializers.SerializerMethodField()
    completed_count = serializers.SerializerMethodField()
    total_points = serializers.SerializerMethodField()
    team = TeamSerializer(read_only=True)
    team_id = serializers.PrimaryKeyRelatedField(
        queryset=Team.objects.all(), source='team', write_only=True, required=False, allow_null=True
    )
    tasks = serializers.SerializerMethodField()

    class Meta:
        model = Sprint
        fields = ['id', 'name', 'goal', 'team', 'team_id', 'status',
                  'start_date', 'end_date', 'task_count', 'completed_count',
                  'total_points', 'tasks', 'created_at']

    def get_task_count(self, obj):
        return obj.tasks.count()

    def get_completed_count(self, obj):
        return obj.tasks.filter(status='done').count()

    def get_total_points(self, obj):
        return sum(t.story_points or 0 for t in obj.tasks.all())

    def get_tasks(self, obj):
        from django.db.models import Count
        qs = (obj.tasks
              .select_related('assignee', 'team', 'linked_bid', 'linked_bid__opportunity')
              .annotate(comment_count=Count('comments', distinct=True),
                        attachment_count=Count('attachments', distinct=True))
              .order_by('position', '-created_at'))
        return TaskCardSerializer(qs, many=True, context=self.context).data


class CommentSerializer(serializers.ModelSerializer):
    author = UserMiniSerializer(read_only=True)

    class Meta:
        model = Comment
        fields = ['id', 'task_id', 'author', 'body', 'is_edited', 'created_at', 'updated_at']
        read_only_fields = ['id', 'task_id', 'author', 'is_edited', 'created_at', 'updated_at']


class AttachmentSerializer(serializers.ModelSerializer):
    uploaded_by = UserMiniSerializer(read_only=True)
    url = serializers.SerializerMethodField()
    is_link = serializers.SerializerMethodField()

    class Meta:
        model = Attachment
        fields = ['id', 'filename', 'size', 'content_type', 'uploaded_by', 'uploaded_at', 'url', 'link_label', 'is_link']

    def get_url(self, obj):
        if obj.url:
            return obj.url
        request = self.context.get('request')
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return None

    def get_is_link(self, obj):
        return bool(obj.url)


class TaskLinkSerializer(serializers.ModelSerializer):
    target_task = serializers.SerializerMethodField()

    class Meta:
        model = TaskLink
        fields = ['id', 'relation', 'target_task']

    def get_target_task(self, obj):
        t = obj.target_task
        return {'id': t.id, 'key': t.key, 'title': t.title, 'status': t.status}


class LinkedBidMiniSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    kc_brand = serializers.CharField()
    status = serializers.CharField()
    opportunity_title = serializers.SerializerMethodField()

    def get_opportunity_title(self, obj):
        return obj.opportunity.title if obj.opportunity_id else None


class TaskCardSerializer(serializers.ModelSerializer):
    """Lightweight card for the board and backlog rows."""
    assignee = UserMiniSerializer(read_only=True)
    is_overdue = serializers.SerializerMethodField()
    comment_count = serializers.IntegerField(read_only=True, default=0)
    attachment_count = serializers.IntegerField(read_only=True, default=0)
    team_name = serializers.CharField(source='team.name', read_only=True, default=None)
    linked_bid_label = serializers.SerializerMethodField()
    sprint_id = serializers.IntegerField(source='sprint.id', read_only=True, default=None)

    class Meta:
        model = Task
        fields = [
            'id', 'key', 'title', 'status', 'priority', 'task_type', 'story_points',
            'sprint_id', 'assignee', 'labels', 'due_date', 'is_overdue', 'position',
            'team_name', 'linked_bid_label', 'comment_count', 'attachment_count',
            'is_recurrence_template', 'recurrence_type',
        ]

    def get_is_overdue(self, obj):
        return bool(obj.due_date and obj.status != 'done' and obj.due_date < timezone.now())

    def get_linked_bid_label(self, obj):
        if obj.linked_bid_id and obj.linked_bid:
            return obj.linked_bid.kc_brand or f"Bid #{obj.linked_bid_id}"
        return None


class TaskDetailSerializer(serializers.ModelSerializer):
    assignee = UserMiniSerializer(read_only=True)
    reporter = UserMiniSerializer(read_only=True)
    created_by = UserMiniSerializer(read_only=True)
    team = TeamSerializer(read_only=True)
    attachments = AttachmentSerializer(many=True, read_only=True)
    links = serializers.SerializerMethodField()
    is_overdue = serializers.SerializerMethodField()
    linked_bid = serializers.SerializerMethodField()

    # write-only
    assignee_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='assignee', write_only=True, required=False, allow_null=True)
    reporter_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='reporter', write_only=True, required=False, allow_null=True)
    team_id = serializers.PrimaryKeyRelatedField(
        queryset=Team.objects.all(), source='team', write_only=True, required=False, allow_null=True)
    linked_bid_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    sprint_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = Task
        fields = [
            'id', 'key', 'title', 'description', 'status', 'priority', 'task_type', 'story_points',
            'assignee', 'reporter', 'created_by', 'team', 'linked_bid',
            'labels', 'start_date', 'due_date', 'is_overdue', 'position',
            'attachments', 'links', 'created_at', 'updated_at',
            'assignee_id', 'reporter_id', 'team_id', 'linked_bid_id', 'sprint_id',
            'recurrence_type', 'recurrence_days', 'recurrence_end_date', 'is_recurrence_template',
        ]
        read_only_fields = ['id', 'key', 'status', 'created_by', 'position', 'created_at', 'updated_at',
                            'is_recurrence_template']

    def get_links(self, obj):
        return TaskLinkSerializer(obj.outgoing_links.select_related('target_task'), many=True).data

    def get_is_overdue(self, obj):
        return bool(obj.due_date and obj.status != 'done' and obj.due_date < timezone.now())

    def get_linked_bid(self, obj):
        if not obj.linked_bid_id or not obj.linked_bid:
            return None
        b = obj.linked_bid
        return {
            'id': b.id,
            'kc_brand': b.kc_brand,
            'status': b.status,
            'opportunity_title': b.opportunity.title if b.opportunity_id else None,
        }


class TaskCreateSerializer(serializers.ModelSerializer):
    assignee_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='assignee', required=False, allow_null=True)
    team_id = serializers.PrimaryKeyRelatedField(
        queryset=Team.objects.all(), source='team', required=False, allow_null=True)
    sprint_id = serializers.PrimaryKeyRelatedField(
        queryset=Sprint.objects.all(), source='sprint', required=False, allow_null=True)
    linked_bid_id = serializers.IntegerField(required=False, allow_null=True)
    status = serializers.ChoiceField(choices=Task.STATUS, required=False)

    recurrence_type = serializers.ChoiceField(choices=Task.RECURRENCE_CHOICES, required=False, default='none')
    recurrence_days = serializers.JSONField(required=False, allow_null=True)
    recurrence_end_date = serializers.DateField(required=False, allow_null=True)

    class Meta:
        model = Task
        fields = [
            'title', 'description', 'priority', 'task_type', 'story_points',
            'status', 'assignee_id', 'team_id', 'sprint_id',
            'linked_bid_id', 'labels', 'start_date', 'due_date',
            'recurrence_type', 'recurrence_days', 'recurrence_end_date',
        ]

    def validate(self, attrs):
        start = attrs.get('start_date')
        due = attrs.get('due_date')
        if start and due and due.date() < start:
            raise serializers.ValidationError({'due_date': 'Due date must be on or after the start date.'})
        return attrs


class BacklogItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = BacklogItem
        fields = ['id', 'title', 'notes', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
