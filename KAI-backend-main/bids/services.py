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
        # Only set FK and nullable datetime fields when non-empty to avoid type coercion errors
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
        'oc_attachments', 'client_bids__client', 'client_bids__assignments__user', 'client_bids__proposal_files'
    ).get(pk=opportunity.pk)
