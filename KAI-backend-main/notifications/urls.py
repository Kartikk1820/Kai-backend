from django.urls import path
from .views import NotificationListView, UnreadCountView, MarkReadView, MarkAllReadView

urlpatterns = [
    path('', NotificationListView.as_view(), name='notification-list'),
    path('unread-count/', UnreadCountView.as_view(), name='notification-unread'),
    path('<int:pk>/read/', MarkReadView.as_view(), name='notification-read'),
    path('mark-all-read/', MarkAllReadView.as_view(), name='notification-mark-all'),
]
