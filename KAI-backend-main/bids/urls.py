from django.urls import path
from .views import (
    BidFilterOptionsView,
    BidOpportunityListCreateView,
    BidOpportunityDetailView,
    ClientBidListView,
    ClientBidDetailView,
    BidSyncStatusView,
    BidSyncNowView,
    ClientListCreateView,
    ClientRetrieveUpdateView,
    PortalCredentialListCreateView,
    PortalCredentialDetailView,
    ClientBidCredentialListCreateView,
    ClientBidCredentialDetailView,
    BidAssignmentListCreateView,
    BidAssignmentDetailView,
    BidOpportunityAttachmentListCreateView,
    BidOpportunityAttachmentDetailView,
    ClientBidProposalFileListCreateView,
    ClientBidProposalFileDetailView,
)

urlpatterns = [
    # Filter options
    path('filter-options/', BidFilterOptionsView.as_view(), name='bid-filter-options'),
    # Opportunities
    path('opportunities/', BidOpportunityListCreateView.as_view(), name='bid-opportunity-list'),
    path('opportunities/<int:pk>/', BidOpportunityDetailView.as_view(), name='bid-opportunity-detail'),
    # OC file attachments
    path('opportunities/<int:opp_pk>/oc-files/', BidOpportunityAttachmentListCreateView.as_view(), name='bid-oc-files-list'),
    path('opportunities/<int:opp_pk>/oc-files/<int:pk>/', BidOpportunityAttachmentDetailView.as_view(), name='bid-oc-file-detail'),
    # Client bids
    path('client-bids/', ClientBidListView.as_view(), name='client-bid-list'),
    path('client-bids/<int:pk>/', ClientBidDetailView.as_view(), name='client-bid-detail'),
    # Portal credentials nested under client-bid (primary)
    path('client-bids/<int:bid_pk>/credentials/', ClientBidCredentialListCreateView.as_view(), name='bid-credential-list'),
    path('client-bids/<int:bid_pk>/credentials/<int:pk>/', ClientBidCredentialDetailView.as_view(), name='bid-credential-detail'),
    # Proposal files
    path('client-bids/<int:bid_pk>/proposal-files/', ClientBidProposalFileListCreateView.as_view(), name='bid-proposal-files-list'),
    path('client-bids/<int:bid_pk>/proposal-files/<int:pk>/', ClientBidProposalFileDetailView.as_view(), name='bid-proposal-file-detail'),
    # Bid assignments (M2M)
    path('client-bids/<int:bid_pk>/assignments/', BidAssignmentListCreateView.as_view(), name='bid-assignment-list'),
    path('assignments/<int:pk>/', BidAssignmentDetailView.as_view(), name='bid-assignment-detail'),
    # Sync
    path('sync-status/', BidSyncStatusView.as_view(), name='bid-sync-status'),
    path('sync-now/', BidSyncNowView.as_view(), name='bid-sync-now'),
    # Clients CRUD
    path('clients/', ClientListCreateView.as_view(), name='client-list'),
    path('clients/<int:pk>/', ClientRetrieveUpdateView.as_view(), name='client-detail'),
    # Portal credentials nested under client (legacy — client-level creds)
    path('clients/<int:client_pk>/credentials/', PortalCredentialListCreateView.as_view(), name='credential-list'),
    path('clients/<int:client_pk>/credentials/<int:pk>/', PortalCredentialDetailView.as_view(), name='credential-detail'),
]
