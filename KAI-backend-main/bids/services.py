"""Bids service layer."""
from django.db import transaction
from core.services import write_audit
from .models import BidOpportunity, ClientBid


@transaction.atomic
def create_opportunity_with_bids(opportunity_data: dict, clients_data: list, actor=None, request=None) -> BidOpportunity:
    """
    Create a BidOpportunity and its associated ClientBids atomically.
    `opportunity_data` is validated_data from BidOpportunitySerializer (Python objects, no nested bids).
    `clients_data` is the raw list from the request (field mapping handled here).
    """
    opportunity = BidOpportunity.objects.create(**opportunity_data)
    write_audit(
        actor=actor,
        model_name='BidOpportunity',
        object_id=opportunity.id,
        action='created',
        new_state='',
        request=request,
    )

    for raw in clients_data:
        bid_kwargs = {
            'opportunity': opportunity,
            'kc_brand': raw.get('brand') or raw.get('kc_brand') or '',
            'status': raw.get('status') or 'in_progress',
            'portal_username': raw.get('portal_username') or '',
            'portal_password': raw.get('portal_password') or '',
            'submission_method': raw.get('submission_method') or '',
            'comments': raw.get('comments') or '',
        }
        if raw.get('client_id'):
            bid_kwargs['client_id'] = raw['client_id']
        if raw.get('internal_deadline'):
            bid_kwargs['internal_deadline'] = raw['internal_deadline']
        if raw.get('date_of_review'):
            bid_kwargs['date_of_review'] = raw['date_of_review']

        cb = ClientBid.objects.create(**bid_kwargs)
        write_audit(
            actor=actor,
            model_name='ClientBid',
            object_id=cb.id,
            action='created',
            new_state=cb.status,
            request=request,
        )

    return BidOpportunity.objects.select_related('prewriter').prefetch_related(
        'oc_attachments', 'client_bids__client', 'client_bids__assignments__user',
        'client_bids__proposal_files', 'client_bids__portal_credentials',
    ).get(pk=opportunity.pk)


@transaction.atomic
def transition_opportunity_status(opportunity: BidOpportunity, new_status: str, actor=None, request=None) -> None:
    """Handle side-effects when BidOpportunity.status changes."""
    old_status = opportunity.status

    if old_status == new_status:
        return

    if new_status == 'pip' and old_status != 'pip':
        _notify_oc_pending_if_needed(opportunity, actor)

    write_audit(
        actor=actor,
        model_name='BidOpportunity',
        object_id=opportunity.id,
        action='status_changed',
        old_state=old_status,
        new_state=new_status,
        request=request,
    )


def _notify_oc_pending_if_needed(opportunity: BidOpportunity, actor) -> None:
    """Create a pending-action notification if the bid has no OC attachments."""
    if opportunity.oc_attachments.exists():
        return

    recipient = opportunity.prewriter or actor
    if not recipient:
        return

    from notifications.models import Notification
    Notification.objects.create(
        recipient=recipient,
        actor=actor,
        kind='bid_oc_pending',
        title='OC document needed',
        body=f'Bid "{opportunity.title}" was moved to PIP but has no OC document attached.',
        link=f'/bids?opportunity_id={opportunity.id}',
    )
