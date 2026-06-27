from django.db import models
from django.conf import settings


class Notification(models.Model):
    KIND_CHOICES = [
        ('leave_approved', 'Leave approved'),
        ('leave_rejected', 'Leave rejected'),
        ('leave_submitted', 'Leave submitted'),
        ('incentive_granted', 'Incentive granted'),
        ('incentive_sent', 'Incentive sent'),
        ('task_assigned', 'Task assigned'),
        ('document_received', 'Document received'),
        ('document_request', 'Document requested'),
        ('document_request_fulfilled', 'Document request fulfilled'),
        ('document_request_declined', 'Document request declined'),
        ('payslip_generated', 'Payslip generated'),
        ('advance_approved', 'Advance approved'),
        ('advance_rejected', 'Advance rejected'),
    ]
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications', db_index=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    kind = models.CharField(max_length=40, choices=KIND_CHOICES)
    title = models.CharField(max_length=255)
    body = models.TextField(blank=True)
    link = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['recipient', 'is_read'])]

    def __str__(self):
        return f"{self.kind} → {self.recipient_id}"
