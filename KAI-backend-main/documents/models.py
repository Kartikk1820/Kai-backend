from django.db import models
from django.conf import settings


def shared_document_path(instance, filename):
    return f"documents/shared/{instance.sender_id}/{filename}"


class SharedDocument(models.Model):
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='sent_documents', db_index=True,
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='received_documents', db_index=True,
    )
    file = models.FileField(upload_to=shared_document_path)
    filename = models.CharField(max_length=255)
    size = models.PositiveIntegerField(default=0)
    content_type = models.CharField(max_length=120, blank=True)
    message = models.TextField(blank=True)
    is_downloaded = models.BooleanField(default=False)
    # links back to the request that this fulfills (nullable)
    fulfills_request = models.OneToOneField(
        'DocumentRequest', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='fulfilled_document',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.filename} ({self.sender_id} → {self.recipient_id})"


class DocumentRequest(models.Model):
    STATUS = [
        ('pending', 'Pending'),
        ('fulfilled', 'Fulfilled'),
        ('declined', 'Declined'),
    ]
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='document_requests_made', db_index=True,
    )
    target = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='document_requests_received', db_index=True,
    )
    document_type = models.CharField(max_length=255)
    message = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS, default='pending', db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Request by {self.requester_id} → {self.target_id}: {self.document_type}"
