from django.db import models
from django.conf import settings


class Client(models.Model):
    name = models.CharField(max_length=255)
    shortcode = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return f"{self.name} ({self.shortcode})"


class BidOpportunity(models.Model):
    agency = models.CharField(max_length=255)
    title = models.CharField(max_length=255)
    solicitation_number = models.CharField(max_length=100, unique=True)
    state = models.CharField(max_length=50)
    due_date = models.DateTimeField()
    bid_link = models.URLField(blank=True)
    category = models.CharField(max_length=100, blank=True)
    source_date = models.DateTimeField(auto_now_add=True)
    pre_bid_info = models.TextField(blank=True)
    qa_notes = models.TextField(blank=True)
    last_synced = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.solicitation_number} — {self.title}"


class ClientBid(models.Model):
    STATUS_CHOICES = [
        ('in_progress', 'In Progress'),
        ('submitted', 'Submitted'),
        ('no_go', 'No Go'),
        ('unsubmitted', 'Unsubmitted'),
        ('cancelled', 'Cancelled'),
        ('postponed', 'Postponed'),
    ]
    SUBMISSION_METHOD_CHOICES = [
        ('portal', 'Portal'),
        ('physical', 'Physical'),
        ('email', 'Email'),
        ('portal_and_physical', 'Portal and Physical'),
        ('fax', 'Fax'),
        ('email_and_physical', 'Email and Physical'),
    ]

    opportunity = models.ForeignKey(BidOpportunity, on_delete=models.CASCADE, related_name='client_bids')
    client = models.ForeignKey(Client, null=True, blank=True, on_delete=models.SET_NULL)
    kc_brand = models.CharField(max_length=100, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='in_progress')
    portal_username = models.CharField(max_length=255, blank=True)
    portal_password = models.CharField(max_length=255, blank=True)
    presales_person = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='presales_bids'
    )
    writer = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='writer_bids'
    )
    internal_deadline = models.DateTimeField(null=True, blank=True)
    submission_method = models.CharField(max_length=30, choices=SUBMISSION_METHOD_CHOICES, blank=True)
    date_of_review = models.DateTimeField(null=True, blank=True)
    comments = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"ClientBid {self.id} — {self.opportunity.title}"


class PortalCredential(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='portal_credentials')
    state = models.CharField(max_length=255, blank=True)
    agency = models.CharField(max_length=255, blank=True)
    portal_name = models.CharField(max_length=255, blank=True)
    username = models.CharField(max_length=255, blank=True)
    password = models.CharField(max_length=255, blank=True)
    link = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['state', 'portal_name']

    def __str__(self):
        return f"{self.client.shortcode} — {self.portal_name or self.agency or 'credential'}"
