"""Notification helper. In-app now; email path is a dormant interface."""
import structlog
from django.core.mail import send_mail
from django.conf import settings
from .models import Notification

logger = structlog.get_logger(__name__)


def notify(*, user, kind, title, body='', link='', actor=None, email=False):
    """Create an in-app notification. Optionally dispatch email (disabled in v1)."""
    if user is None:
        return None
    n = Notification.objects.create(
        recipient=user, actor=actor, kind=kind, title=title, body=body, link=link,
    )
    if email:
        try:
            send_mail(title, body or title, settings.DEFAULT_FROM_EMAIL, [user.email],
                      fail_silently=True)
        except Exception:
            logger.warning('notification_email_failed', recipient=user.id, kind=kind)
    return n
