"""Bids service layer.

NOTE: the legacy phantom `Bid` FSM model has been removed. The real domain is
BidOpportunity + ClientBid (see models.py). Bid-side transition services will be
rebuilt here when the Bids module is implemented; Tasks links to ClientBid only.
"""
