from django.urls import path
from .views import (
    SendDocumentView, InboxView, SentView, DocumentDownloadView, DocumentDeleteView,
    DocumentRequestListCreateView, DocumentRequestActionView,
)

urlpatterns = [
    path('share/', SendDocumentView.as_view(), name='document-share'),
    path('inbox/', InboxView.as_view(), name='document-inbox'),
    path('sent/', SentView.as_view(), name='document-sent'),
    path('<int:pk>/download/', DocumentDownloadView.as_view(), name='document-download'),
    path('<int:pk>/', DocumentDeleteView.as_view(), name='document-delete'),
    path('requests/', DocumentRequestListCreateView.as_view(), name='document-requests'),
    path('requests/<int:pk>/', DocumentRequestActionView.as_view(), name='document-request-action'),
]
