from rest_framework import views, generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from django.db.models import Q, Prefetch
from django.contrib.auth import get_user_model
from django.apps import apps
from django.conf import settings
from django.utils import timezone
import hmac
import hashlib
import json
import structlog

from .models import Client, BidOpportunity, ClientBid, BidAssignment, PortalCredential
from .serializers import (
    ClientSerializer, ClientDetailSerializer, BidOpportunitySerializer,
    ClientBidSerializer, BidAssignmentSerializer, UserBidSerializer, PortalCredentialSerializer
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
        qs_opportunities = qs_opportunities.filter(client_bids__assignments__user_id=writer_id).distinct()

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
        
        # Fetch all active internal employees (excluding clients) for these dropdowns
        internal_users = User.objects.filter(is_active=True).exclude(role='Client')
        
        writers = UserBidSerializer(internal_users, many=True).data
        presales = UserBidSerializer(internal_users, many=True).data
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
            Prefetch('client_bids', queryset=ClientBid.objects.select_related('client').prefetch_related(
                Prefetch('assignments', queryset=BidAssignment.objects.select_related('user'))
            ))
        )
        qs = _apply_bid_filters(qs, request.query_params)
        return Response(BidOpportunitySerializer(qs, many=True).data)

    def post(self, request):
        from .services import create_opportunity_with_bids
        # Accept both nested {opportunity, clients} shape (from the modal) and flat shape
        opp_raw = request.data.get('opportunity', request.data)
        clients_raw = request.data.get('clients', [])

        serializer = BidOpportunitySerializer(data=opp_raw)
        serializer.is_valid(raise_exception=True)

        opportunity = create_opportunity_with_bids(
            opportunity_data=serializer.validated_data,
            clients_data=clients_raw,
            actor=request.user,
            request=request,
        )
        return Response(BidOpportunitySerializer(opportunity).data, status=status.HTTP_201_CREATED)


# ─── 3. Flat ClientBids list ──────────────────────────────────────────────────

class ClientBidListView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        opp_qs = _apply_bid_filters(BidOpportunity.objects.all(), request.query_params)
        qs = ClientBid.objects.filter(opportunity__in=opp_qs).select_related(
            'client', 'opportunity'
        ).prefetch_related(
            Prefetch('assignments', queryset=BidAssignment.objects.select_related('user'))
        )
        statuses = request.query_params.getlist('status')
        if statuses:
            qs = qs.filter(status__in=statuses)
        writer_id = request.query_params.get('writer_id')
        if writer_id:
            qs = qs.filter(assignments__user_id=writer_id)
        client_id = request.query_params.get('client_id')
        if client_id:
            qs = qs.filter(client_id=client_id)
        return Response(ClientBidSerializer(qs, many=True).data)

    def post(self, request):
        serializer = ClientBidSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # We need opportunity_id from request data
        opportunity_id = request.data.get('opportunity_id')
        if not opportunity_id:
            return Response({"error": "opportunity_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            opp = BidOpportunity.objects.get(id=opportunity_id)
        except BidOpportunity.DoesNotExist:
            return Response({"error": "Opportunity not found"}, status=status.HTTP_404_NOT_FOUND)

        client_bid = serializer.save(opportunity=opp)
        
        # Log activity
        ActivityLog = apps.get_model('core', 'ActivityLog')
        client_name = client_bid.client.name if client_bid.client else client_bid.kc_brand
        ActivityLog.objects.create(
            actor=request.user,
            action_type='bid_created',
            target_model='ClientBid',
            target_id=str(client_bid.id),
            description=f"Added client '{client_name}' to opportunity '{opp.title}'"
        )
        
        return Response(ClientBidSerializer(client_bid).data, status=status.HTTP_201_CREATED)


# ─── 4. Single BidOpportunity detail ─────────────────────────────────────────

class BidOpportunityDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    queryset = BidOpportunity.objects.prefetch_related(
        Prefetch('client_bids', queryset=ClientBid.objects.select_related('client').prefetch_related(
            Prefetch('assignments', queryset=BidAssignment.objects.select_related('user'))
        ))
    )
    serializer_class = BidOpportunitySerializer


# ─── 6. Update ClientBid ──────────────────────────────────────────────────────

class ClientBidDetailView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated]
    queryset = ClientBid.objects.select_related('client').prefetch_related('assignments__user')
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


import pandas as pd
import uuid

# ─── 8. Trigger Manual Sync ───────────────────────────────────────────────────

class BidSyncNowView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        file = request.FILES.get('file')
        if not file:
            return Response({"error": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            dfs = pd.read_excel(file, sheet_name=None)
            imported_count = 0
            
            for sheet_name, df in dfs.items():
                for index, row in df.iterrows():
                    solicitation = str(row.get('Solicitation Number', '')).strip()
                    if not solicitation or solicitation == 'nan':
                        solicitation = f"MIGRATED-{uuid.uuid4().hex[:8]}"
    
                    title = str(row.get('Title', '')).strip()
                    if not title or title == 'nan':
                        continue  # Skip empty rows
    
                    agency = str(row.get('Agency', '')).strip()
                    state = str(row.get('State', '')).strip()
                    due_date_raw = row.get('Due date')
                    if pd.isna(due_date_raw):
                        due_date = timezone.now()
                    else:
                        due_date = pd.to_datetime(due_date_raw)
                        if due_date.tzinfo is None:
                            due_date = timezone.make_aware(due_date)
    
                    bid_link = str(row.get('Bid Link', '')).strip()
                    category = str(row.get('Category', '')).strip()
                    source_date_raw = row.get('SOURCE DATE')
                    if pd.isna(source_date_raw):
                        source_date = timezone.now()
                    else:
                        source_date = pd.to_datetime(source_date_raw)
                        if source_date.tzinfo is None:
                            source_date = timezone.make_aware(source_date)
                        
                    pre_bid = str(row.get('Pre-bid', '')).strip()
                    qa_notes = str(row.get('Q&A', '')).strip()
    
                    opportunity, created = BidOpportunity.objects.update_or_create(
                        solicitation_number=solicitation,
                        defaults={
                            'agency': agency if agency != 'nan' else '',
                            'title': title,
                            'state': state if state != 'nan' else '',
                            'due_date': due_date,
                            'bid_link': bid_link if bid_link != 'nan' else '',
                            'category': category if category != 'nan' else '',
                            'pre_bid_info': pre_bid if pre_bid != 'nan' else '',
                            'qa_notes': qa_notes if qa_notes != 'nan' else '',
                        }
                    )
    
                    # ClientBid data
                    subm = str(row.get('Subm', '')).strip()
                    status_raw = str(row.get('Status', '')).strip()
                    password = str(row.get('Password', '')).strip()
                    pre_sales_name = str(row.get('Pre-Sales', '')).strip()
                    writer_name = str(row.get('Writer', '')).strip()
                    comments = str(row.get('Comments', '')).strip()
                    if comments == 'nan':
                        comments = ''
                        
                    notes_to_add = []
                    notes_to_add.append(f"financial year:{sheet_name}")
    
                    # Status mapping
                    status_mapping = {
                        'no-go': 'no_go',
                        'in-progress': 'in_progress',
                        'submitted': 'submitted',
                        'unsubmitted': 'unsubmitted',
                        'cancelled': 'cancelled',
                        'postponed': 'postponed'
                    }
                    status_clean = status_mapping.get(status_raw.lower(), 'in_progress')
    
                    presales_user = None
                    if pre_sales_name and pre_sales_name != 'nan':
                        presales_user = User.objects.filter(first_name__icontains=pre_sales_name).first()
                        if not presales_user:
                            notes_to_add.append(f"presale:{pre_sales_name}")

                    writer_user = None
                    if writer_name and writer_name != 'nan':
                        writer_user = User.objects.filter(first_name__icontains=writer_name).first()
                        if not writer_user:
                            notes_to_add.append(f"writer:{writer_name}")

                    if notes_to_add:
                        if comments:
                            comments += "\n" + "\n".join(notes_to_add)
                        else:
                            comments = "\n".join(notes_to_add)

                    client_bid, _ = ClientBid.objects.update_or_create(
                        opportunity=opportunity,
                        kc_brand=subm if subm != 'nan' else '',
                        defaults={
                            'status': status_clean,
                            'portal_password': password if password != 'nan' else '',
                            'comments': comments,
                        }
                    )

                    if writer_user:
                        BidAssignment.objects.update_or_create(
                            client_bid=client_bid, user=writer_user,
                            defaults={'role': 'writer'}
                        )
                    if presales_user:
                        BidAssignment.objects.update_or_create(
                            client_bid=client_bid, user=presales_user,
                            defaults={'role': 'presales'}
                        )
                    imported_count += 1
                
            return Response({"message": f"Successfully imported {imported_count} records."}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Excel import error: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ─── 9. Clients list + create ─────────────────────────────────────────────────

class ClientListCreateView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        clients = Client.objects.prefetch_related('portal_credentials').all()
        return Response(ClientDetailSerializer(clients, many=True).data)

    def post(self, request):
        serializer = ClientSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        client = serializer.save()
        return Response(ClientDetailSerializer(client).data, status=status.HTTP_201_CREATED)


class ClientRetrieveUpdateView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Client.objects.prefetch_related('portal_credentials').all()
    serializer_class = ClientDetailSerializer

    def get_serializer_class(self):
        if self.request.method in ('PUT', 'PATCH'):
            return ClientSerializer
        return ClientDetailSerializer

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = ClientSerializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        client = serializer.save()
        return Response(ClientDetailSerializer(Client.objects.prefetch_related('portal_credentials').get(pk=client.pk)).data)


# ─── 10. Portal credentials ────────────────────────────────────────────────────

class PortalCredentialListCreateView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, client_pk):
        creds = PortalCredential.objects.filter(client_id=client_pk)
        return Response(PortalCredentialSerializer(creds, many=True).data)

    def post(self, request, client_pk):
        get_object_or_404 = __import__('django.shortcuts', fromlist=['get_object_or_404']).get_object_or_404
        client = get_object_or_404(Client, pk=client_pk)
        serializer = PortalCredentialSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cred = serializer.save(client=client)
        write_audit = __import__('core.services', fromlist=['write_audit']).write_audit
        write_audit(actor=request.user, model_name='PortalCredential', object_id=cred.id, action='created', request=request)
        return Response(PortalCredentialSerializer(cred).data, status=status.HTTP_201_CREATED)


class PortalCredentialDetailView(views.APIView):
    permission_classes = [IsAuthenticated]

    def _get(self, client_pk, pk):
        from django.shortcuts import get_object_or_404
        return get_object_or_404(PortalCredential, pk=pk, client_id=client_pk)

    def patch(self, request, client_pk, pk):
        cred = self._get(client_pk, pk)
        serializer = PortalCredentialSerializer(cred, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(PortalCredentialSerializer(cred).data)

    def delete(self, request, client_pk, pk):
        cred = self._get(client_pk, pk)
        cred.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ─── 11. Bid Assignments ───────────────────────────────────────────────────────

class BidAssignmentListCreateView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, bid_pk):
        from django.shortcuts import get_object_or_404
        bid = get_object_or_404(ClientBid, pk=bid_pk)
        serializer = BidAssignmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            assignment = serializer.save(client_bid=bid)
        except Exception:
            return Response({'error': 'User already assigned to this bid.'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(BidAssignmentSerializer(assignment).data, status=status.HTTP_201_CREATED)


class BidAssignmentDetailView(views.APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        from django.shortcuts import get_object_or_404
        assignment = get_object_or_404(BidAssignment, pk=pk)
        assignment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def patch(self, request, pk):
        from django.shortcuts import get_object_or_404
        assignment = get_object_or_404(BidAssignment, pk=pk)
        serializer = BidAssignmentSerializer(assignment, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(BidAssignmentSerializer(assignment).data)
