"""Documents Celery tasks."""
from celery import shared_task
from django.utils.timezone import now
from datetime import timedelta
import structlog

logger = structlog.get_logger(__name__)


@shared_task
def escalate_stale_approvals():
    """
    Runs every 30 minutes. Finds pending document-send approvals where the
    configured escalation window has elapsed, marks them 'escalated', and
    notifies all Admin users so they can act.
    """
    from .models import DocumentSendApproval
    from notifications.services import notify
    from django.contrib.auth import get_user_model

    User = get_user_model()
    admins = list(User.objects.filter(user_type='Admin'))

    pending = DocumentSendApproval.objects.filter(status='pending').select_related(
        'sender', 'recipient', 'approver'
    )
    escalated_count = 0
    for appr in pending:
        cutoff = appr.created_at + timedelta(minutes=appr.escalation_minutes)
        if now() < cutoff:
            continue

        appr.status = 'escalated'
        appr.escalated_at = now()
        appr.save(update_fields=['status', 'escalated_at', 'updated_at'])
        escalated_count += 1

        for admin in admins:
            notify(
                user=admin,
                kind='document_approval_escalated',
                title=f"Approval escalated: {appr.sender.full_name} → {appr.recipient.full_name}",
                body=f"{appr.filename} — manager did not act within {appr.escalation_minutes} min",
                link='/documents?tab=approvals',
                actor=appr.sender,
            )
        notify(
            user=appr.sender,
            kind='document_approval_escalated',
            title="Your document approval was escalated to Admin",
            body=f"{appr.filename} — your manager did not respond in time",
            link='/documents?tab=sent',
            actor=appr.sender,
        )
        logger.info('approval_escalated', approval_id=appr.id, sender=str(appr.sender))

    return {'escalated': escalated_count}
