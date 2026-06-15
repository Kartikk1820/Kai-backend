"""Shared service-layer helpers: audit logging and request context."""
from .models import AuditLog


def client_ip(request):
    if request is None or not hasattr(request, 'META'):
        return None
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def write_audit(*, actor=None, actor_system=None, model_name, object_id,
                action='', old_state=None, new_state='', request=None, context=None):
    """Create an AuditLog row. Call inside the same transaction as the change."""
    return AuditLog.objects.create(
        actor=actor if (actor and getattr(actor, 'is_authenticated', False)) else None,
        actor_system=actor_system,
        model_name=model_name,
        object_id=str(object_id),
        action=action,
        old_state=old_state,
        new_state=new_state or '',
        ip_address=client_ip(request),
        context=context,
    )
