from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _


class CustomUserManager(BaseUserManager):
    """Email is the unique identifier for authentication instead of username."""

    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_('The Email must be set'))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('role', 'Admin')
        extra_fields.setdefault('must_change_password', False)
        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = None
    email = models.EmailField(_('email address'), unique=True)

    ROLE_CHOICES = [
        ('Admin', 'Admin'),
        ('Manager', 'Manager'),
        ('Employee', 'Employee'),
        ('Client', 'Client'),
    ]
    is_active = models.BooleanField(default=True, db_column='is_activated')

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='Employee', db_index=True)
    sub_position = models.CharField(max_length=100, null=True, blank=True)
    manager = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.SET_NULL, related_name='subordinates'
    )

    phone_number = models.CharField(max_length=20, null=True, blank=True)
    date_of_joining = models.DateField(null=True, blank=True)
    entity = models.CharField(max_length=100, null=True, blank=True)

    # Forced one-time password change after admin creates/resets the account.
    must_change_password = models.BooleanField(default=True)

    state = models.CharField(max_length=100, null=True, blank=True)
    present_location = models.CharField(max_length=255, null=True, blank=True)
    job_id = models.CharField(max_length=100, null=True, blank=True)

    # Per-user permission overrides on top of group permissions.
    extra_permissions = models.JSONField(default=list, blank=True)   # granted keys
    revoked_permissions = models.JSONField(default=list, blank=True)  # revoked keys

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.email} ({self.role})"

    @property
    def full_name(self):
        name = f"{self.first_name} {self.last_name}".strip()
        return name or self.email

    @property
    def avatar_initials(self):
        if self.first_name and self.last_name:
            return f"{self.first_name[0]}{self.last_name[0]}".upper()
        return (self.email[:2].upper() if self.email else '??')

    # ----- RBAC -----
    def effective_permissions(self):
        """Union of group permission keys + direct grants, minus revokes.
        Admins implicitly hold every catalog key."""
        from core.permissions_catalog import ALL_KEYS
        if self.is_superuser or self.role == 'Admin':
            return set(ALL_KEYS)
        keys = set()
        for ur in self.user_roles.select_related('role').all():
            keys |= set(ur.role.permission_keys or [])
        keys |= set(self.extra_permissions or [])
        keys -= set(self.revoked_permissions or [])
        return keys

    def has_perm_key(self, key):
        return key in self.effective_permissions()


class Position(models.Model):
    """Named position (e.g. "Proposal Writer") that bundles one or more RBAC roles."""
    name = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=255, blank=True, default='')
    role_ids = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name
