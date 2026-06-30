from rest_framework import generics, views, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Notification
from .serializers import NotificationSerializer


class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Notification.objects.filter(recipient=self.request.user)
        if self.request.query_params.get('unread') == 'true':
            qs = qs.filter(is_read=False)
        return qs


class UnreadCountView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        return Response({'unread': count})


class MarkReadView(views.APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        try:
            n = Notification.objects.get(pk=pk, recipient=request.user)
        except Notification.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        n.is_read = True
        n.save(update_fields=['is_read'])
        return Response(NotificationSerializer(n).data)


class MarkAllReadView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        return Response({'detail': 'All marked read.'})


from django.contrib.auth import get_user_model
from .services import notify

User = get_user_model()

class ManualNotificationView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not (request.user.user_type == 'Admin' or getattr(request.user, 'is_superuser', False)):
            return Response({'detail': 'Not allowed.'}, status=status.HTTP_403_FORBIDDEN)
            
        title = request.data.get('title')
        body = request.data.get('body', '')
        targets = request.data.get('targets') # 'all' or list of ids
        
        if not title or not targets:
            return Response({'detail': 'Title and targets are required.'}, status=status.HTTP_400_BAD_REQUEST)
            
        users_to_notify = []
        if targets == 'all':
            users_to_notify = list(User.objects.filter(is_active=True))
        elif isinstance(targets, list):
            users_to_notify = list(User.objects.filter(id__in=targets, is_active=True))
        else:
            return Response({'detail': 'Invalid targets format.'}, status=status.HTTP_400_BAD_REQUEST)
            
        sent_count = 0
        for u in users_to_notify:
            notify(user=u, kind='manual_notification', title=title, body=body, actor=request.user)
            sent_count += 1
            
        return Response({'detail': f'Sent {sent_count} notifications.'}, status=status.HTTP_201_CREATED)
