from django.urls import path
from .views import (
    BidFilterOptionsView,
    BidOpportunityListCreateView,
    BidOpportunityDetailView,
    ClientBidListView,
    ClientBidDetailView,
    BidSyncStatusView,
    BidSyncNowView,
)

urlpatterns = [
    # 1. Filter options
    path('filter-options/', BidFilterOptionsView.as_view(), name='bid-filter-options'),
    # 2. Opportunities list + create
    path('opportunities/', BidOpportunityListCreateView.as_view(), name='bid-opportunity-list'),
    # 4. Single opportunity detail
    path('opportunities/<int:pk>/', BidOpportunityDetailView.as_view(), name='bid-opportunity-detail'),
    # 3. Flat client-bids list
    path('client-bids/', ClientBidListView.as_view(), name='client-bid-list'),
    # 6. Update a client-bid
    path('client-bids/<int:pk>/', ClientBidDetailView.as_view(), name='client-bid-detail'),
    # 7. Sync status
    path('sync-status/', BidSyncStatusView.as_view(), name='bid-sync-status'),
    # 8. Trigger sync
    path('sync-now/', BidSyncNowView.as_view(), name='bid-sync-now'),
]
