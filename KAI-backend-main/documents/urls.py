from django.urls import path
from .views import (
    SendDocumentView, InboxView, SentView, DocumentDownloadView, DocumentDeleteView,
    DocumentMarkReadView, DocumentRequestListCreateView, DocumentRequestActionView,
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
]
