from rest_framework import views, generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from django.db.models import Q, Prefetch
from django.contrib.auth import get_user_model
from django.conf import settings
from django.utils import timezone
import hmac
import hashlib
import json
import structlog

from .models import Client, BidOpportunity, ClientBid
from .serializers import (
    ClientSerializer, BidOpportunitySerializer,
    ClientBidSerializer, UserBidSerializer
)

logger = structlog.get_logger(__name__)
User = get_user_model()


# ─── Existing Webhook ──────────────────────────────────────────────────────────

class GoogleSheetsWebhookView(views.APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        signature_header = request.headers.get('X-Hub-Signature-256')

        if not signature_header:
            logger.warning("webhook_missing_signature")
            raise PermissionDenied("Missing signature")

        try:
            algo, signature = signature_header.split('=')
            if algo != 'sha256':
                raise ValueError
        except ValueError:
            logger.warning("webhook_invalid_signature_format")
            raise PermissionDenied("Invalid signature format")

        secret = settings.GOOGLE_SHEETS_WEBHOOK_SECRET.encode('utf-8')
        mac = hmac.new(secret, msg=request.body, digestmod=hashlib.sha256)
        expected_signature = mac.hexdigest()

        if not hmac.compare_digest(expected_signature, signature):
            logger.warning("webhook_signature_mismatch")
            raise PermissionDenied("Invalid signature")

        try:
            payload = json.loads(request.body)
            logger.info("webhook_processed_successfully")
            return Response({"message": "Webhook received and verified"})
        except json.JSONDecodeError:
            logger.warning("webhook_invalid_json")
            return Response({"error": "Invalid JSON"}, status=400)


# ─── Helper: shared filter queryset ───────────────────────────────────────────

def _apply_bid_filters(qs_opportunities, params):
    """Apply common filter params to a BidOpportunity queryset."""
    search = params.get('search')
    if search:
        qs_opportunities = qs_opportunities.filter(
            Q(title__icontains=search) | Q(agency__icontains=search)
        )

    state = params.get('state')
    if state:
        qs_opportunities = qs_opportunities.filter(state=state)

    category = params.get('category')
    if category:
        qs_opportunities = qs_opportunities.filter(category=category)

    statuses = params.getlist('status')
    if statuses:
        qs_opportunities = qs_opportunities.filter(client_bids__status__in=statuses).distinct()

    writer_id = params.get('writer_id')
    if writer_id:
        qs_opportunities = qs_opportunities.filter(client_bids__writer_id=writer_id).distinct()

    client_id = params.get('client_id')
    if client_id:
        qs_opportunities = qs_opportunities.filter(client_bids__client_id=client_id).distinct()

    date_from = params.get('date_from')
    if date_from:
        qs_opportunities = qs_opportunities.filter(due_date__gte=date_from)

    date_to = params.get('date_to')
    if date_to:
        qs_opportunities = qs_opportunities.filter(due_date__lte=date_to)

    return qs_opportunities


# ─── 1. Filter Options ────────────────────────────────────────────────────────

class BidFilterOptionsView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        clients = ClientSerializer(Client.objects.all(), many=True).data
        writers = UserBidSerializer(
            User.objects.filter(writer_bids__isnull=False).distinct(), many=True
        ).data
        presales = UserBidSerializer(
            User.objects.filter(presales_bids__isnull=False).distinct(), many=True
        ).data
        states = list(
            BidOpportunity.objects.exclude(state='').values_list('state', flat=True).distinct()
        )
        categories = list(
            BidOpportunity.objects.exclude(category='').values_list('category', flat=True).distinct()
        )
        statuses = [c[0] for c in ClientBid.STATUS_CHOICES]

        return Response({
            "clients": clients,
            "writers": writers,
            "presales": presales,
            "states": states,
            "categories": categories,
            "statuses": statuses,
        })


# ─── 2. List BidOpportunities (grouped) ───────────────────────────────────────

class BidOpportunityListCreateView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = BidOpportunity.objects.prefetch_related(
            Prefetch('client_bids', queryset=ClientBid.objects.select_related('client', 'presales_person', 'writer'))
        )
        qs = _apply_bid_filters(qs, request.query_params)
        return Response(BidOpportunitySerializer(qs, many=True).data)

    def post(self, request):
        serializer = BidOpportunitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


# ─── 3. Flat ClientBids list ──────────────────────────────────────────────────

class ClientBidListView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Apply opportunity-level filters (search, state, category, dates, etc.)
        opp_qs = _apply_bid_filters(BidOpportunity.objects.all(), request.query_params)
        qs = ClientBid.objects.filter(opportunity__in=opp_qs).select_related(
            'client', 'presales_person', 'writer', 'opportunity'
        )
        # Apply ClientBid-direct filters
        statuses = request.query_params.getlist('status')
        if statuses:
            qs = qs.filter(status__in=statuses)
        writer_id = request.query_params.get('writer_id')
        if writer_id:
            qs = qs.filter(writer_id=writer_id)
        client_id = request.query_params.get('client_id')
        if client_id:
            qs = qs.filter(client_id=client_id)
        return Response(ClientBidSerializer(qs, many=True).data)


# ─── 4. Single BidOpportunity detail ─────────────────────────────────────────

class BidOpportunityDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    queryset = BidOpportunity.objects.prefetch_related(
        Prefetch('client_bids', queryset=ClientBid.objects.select_related('client', 'presales_person', 'writer'))
    )
    serializer_class = BidOpportunitySerializer


# ─── 6. Update ClientBid ──────────────────────────────────────────────────────

class ClientBidDetailView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated]
    queryset = ClientBid.objects.select_related('client', 'presales_person', 'writer')
    serializer_class = ClientBidSerializer
    http_method_names = ['patch']

    def patch(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


# ─── 7. Sync Status ───────────────────────────────────────────────────────────

class BidSyncStatusView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        latest = BidOpportunity.objects.exclude(last_synced=None).order_by('-last_synced').first()
        return Response({
            "last_synced": latest.last_synced if latest else None,
            "is_syncing": False,
            "sync_errors": [],
        })


# ─── 8. Trigger Manual Sync ───────────────────────────────────────────────────

class BidSyncNowView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # TODO: wire to Celery task when external sync implemented
        logger.info("manual_sync_triggered", user=request.user.email)
        return Response({"message": "Sync started."}, status=status.HTTP_202_ACCEPTED)
