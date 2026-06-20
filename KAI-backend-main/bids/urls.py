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
)

urlpatterns = [
    # Filter options
    path('filter-options/', BidFilterOptionsView.as_view(), name='bid-filter-options'),
    # Opportunities
    path('opportunities/', BidOpportunityListCreateView.as_view(), name='bid-opportunity-list'),
    path('opportunities/<int:pk>/', BidOpportunityDetailView.as_view(), name='bid-opportunity-detail'),
    # Client bids
    path('client-bids/', ClientBidListView.as_view(), name='client-bid-list'),
    path('client-bids/<int:pk>/', ClientBidDetailView.as_view(), name='client-bid-detail'),
    # Sync
    path('sync-status/', BidSyncStatusView.as_view(), name='bid-sync-status'),
    path('sync-now/', BidSyncNowView.as_view(), name='bid-sync-now'),
    # Clients CRUD
    path('clients/', ClientListCreateView.as_view(), name='client-list'),
    path('clients/<int:pk>/', ClientRetrieveUpdateView.as_view(), name='client-detail'),
    # Portal credentials (nested under client)
    path('clients/<int:client_pk>/credentials/', PortalCredentialListCreateView.as_view(), name='credential-list'),
    path('clients/<int:client_pk>/credentials/<int:pk>/', PortalCredentialDetailView.as_view(), name='credential-detail'),
]
