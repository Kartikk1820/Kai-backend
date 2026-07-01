from django.urls import path
from .views import (
    SendDocumentView, InboxView, SentView, DocumentDownloadView, DocumentDeleteView,
    DocumentMarkReadView, DocumentRequestListCreateView, DocumentRequestActionView,
    DocumentSendApprovalListView, DocumentSendApprovalActionView,
)

urlpatterns = [
    path('share/', SendDocumentView.as_view(), name='document-share'),
    path('inbox/', InboxView.as_view(), name='document-inbox'),
    path('sent/', SentView.as_view(), name='document-sent'),
    path('<int:pk>/download/', DocumentDownloadView.as_view(), name='document-download'),
    path('<int:pk>/', DocumentDeleteView.as_view(), name='document-delete'),
    path('<int:pk>/mark-read/', DocumentMarkReadView.as_view(), name='document-mark-read'),
    path('requests/', DocumentRequestListCreateView.as_view(), name='document-requests'),
    path('requests/<int:pk>/', DocumentRequestActionView.as_view(), name='document-request-action'),
    path('approvals/', DocumentSendApprovalListView.as_view(), name='document-approvals'),
    path('approvals/<int:pk>/', DocumentSendApprovalActionView.as_view(), name='document-approval-action'),
]
