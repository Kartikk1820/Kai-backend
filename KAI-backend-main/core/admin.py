from django.contrib import admin
from .models import AuditLog, Role, UserRole


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'actor', 'model_name', 'object_id', 'action', 'old_state', 'new_state')
    list_filter = ('model_name', 'action')
    search_fields = ('object_id',)
    readonly_fields = [f.name for f in AuditLog._meta.fields]


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_system')


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'assigned_at')
