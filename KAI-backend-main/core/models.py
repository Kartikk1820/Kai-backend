from django.db import models
from django.conf import settings


class AuditLog(models.Model):
    """Immutable record of every state change across the system."""
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='audit_logs',
    )
    actor_system = models.CharField(
        max_length=50, null=True, blank=True,
        help_text="e.g., 'System', 'Celery', 'Webhook'",
    )
    model_name = models.CharField(max_length=100, db_index=True)
    object_id = models.CharField(max_length=255, db_index=True)
    action = models.CharField(max_length=50, blank=True, help_text="e.g. created, transition, deleted")
    old_state = models.CharField(max_length=50, null=True, blank=True)
    new_state = models.CharField(max_length=50, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    context = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['model_name', 'object_id']),
        ]

    def __str__(self):
        actor_name = getattr(self.actor, 'email', None) or self.actor_system or 'system'
        return f"{self.timestamp} | {actor_name} | {self.model_name} {self.object_id} | {self.old_state} -> {self.new_state}"


class UserTypePermissions(models.Model):
    """
    Stores default permission keys for each user_type.
    effective_permissions() merges these in automatically — no manual role
    assignment needed. Admin user_type bypasses this (always gets ALL_KEYS).
    """
    USER_TYPE_CHOICES = [
        ('Employee', 'Employee'),
        ('Manager', 'Manager'),
        ('Client', 'Client'),
    ]
    user_type = models.CharField(max_length=20, unique=True, choices=USER_TYPE_CHOICES)
    permission_keys = models.JSONField(default=list, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['user_type']
        verbose_name = 'User Type Permissions'
        verbose_name_plural = 'User Type Permissions'

    def __str__(self):
        return f"{self.user_type} ({len(self.permission_keys)} perms)"


class Role(models.Model):
    """A named bundle of permission keys (our 'Group'). Admin-managed."""
    name = models.CharField(max_length=80, unique=True)
    description = models.CharField(max_length=255, blank=True)
    permission_keys = models.JSONField(default=list, blank=True)
    is_system = models.BooleanField(default=False, help_text="Seeded roles cannot be deleted")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class UserRole(models.Model):
    """M2M between users and roles (a user may hold many roles)."""
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='user_roles')
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='members')
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'role')

    def __str__(self):
        return f"{self.user_id} → {self.role_id}"
