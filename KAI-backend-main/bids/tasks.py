"""Bids Celery tasks.

The legacy `create_default_tasks_for_bid` referenced a non-existent `Bid` model
and has been removed. Auto-task creation for bids will be reintroduced with the
Bids module against the real ClientBid model.
"""
