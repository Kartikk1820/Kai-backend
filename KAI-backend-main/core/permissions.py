"""
DRF permission classes driven by the permission catalog.
Effective permissions = (union of group perms) + direct grants - direct revokes,
computed on the User model (see users.models.User.effective_permissions).
"""
from rest_framework.permissions import BasePermission, SAFE_METHODS


class HasPermissionKey(BasePermission):
    """
    Usage:  permission_classes = [HasPermissionKey.of('hr.run_payroll')]
    """
    required_key = None

    @classmethod
    def of(cls, key):
        return type(f'HasPerm_{key}', (cls,), {'required_key': key})

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if self.required_key is None:
            return True
        return user.has_perm_key(self.required_key)


class HasAnyPermissionKey(BasePermission):
    """Grants access if the user holds ANY of the given keys."""
    keys = ()

    @classmethod
    def of(cls, *keys):
        return type('HasAnyPerm', (cls,), {'keys': keys})

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        return any(user.has_perm_key(k) for k in self.keys)


class ReadOnly(BasePermission):
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS
