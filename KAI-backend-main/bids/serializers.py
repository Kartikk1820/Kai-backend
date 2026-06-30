from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Client, BidOpportunity, ClientBid, BidAssignment, PortalCredential

User = get_user_model()


CLIENT_INFO_FIELDS = [
    'owner_name', 'incorporation_date', 'state_of_incorporation', 'corporation_type',
    'fein', 'duns', 'cage_code', 'everify_no', 'website',
    'address', 'phone', 'email', 'fax', 'notes',
]


class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = ['id', 'name', 'shortcode'] + CLIENT_INFO_FIELDS


class UserBidSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    avatar_initials = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'full_name', 'email', 'avatar_initials']

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.email

    def get_avatar_initials(self, obj):
        if obj.first_name and obj.last_name:
            return f"{obj.first_name[0]}{obj.last_name[0]}".upper()
        return obj.email[0].upper() if obj.email else "??"


class BidAssignmentSerializer(serializers.ModelSerializer):
    user = UserBidSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='user', write_only=True
    )

    class Meta:
        model = BidAssignment
        fields = ['id', 'user', 'user_id', 'role', 'assigned_at']
        read_only_fields = ['id', 'assigned_at']


class ClientBidSerializer(serializers.ModelSerializer):
    client = ClientSerializer(read_only=True)
    assignments = BidAssignmentSerializer(many=True, read_only=True)
    opportunity_title = serializers.CharField(source='opportunity.title', read_only=True)
    opportunity_agency = serializers.CharField(source='opportunity.agency', read_only=True)
    opportunity_state = serializers.CharField(source='opportunity.state', read_only=True)
    opportunity_due_date = serializers.DateTimeField(source='opportunity.due_date', read_only=True)

    client_id = serializers.PrimaryKeyRelatedField(
        queryset=Client.objects.all(), source='client',
        write_only=True, required=False, allow_null=True
    )

    class Meta:
        model = ClientBid
        fields = [
            'id', 'opportunity_id', 'client', 'kc_brand', 'status',
            'portal_username', 'portal_password',
            'assignments',
            'internal_deadline', 'submission_method',
            'date_of_review', 'comments',
            'created_at', 'updated_at',
            'client_id',
            'opportunity_title', 'opportunity_agency', 'opportunity_state', 'opportunity_due_date',
        ]
        read_only_fields = ['id', 'opportunity_id', 'created_at', 'updated_at']


class PortalCredentialSerializer(serializers.ModelSerializer):
    class Meta:
        model = PortalCredential
        fields = ['id', 'client_id', 'state', 'agency', 'portal_name', 'username', 'password', 'link', 'notes', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class ClientDetailSerializer(serializers.ModelSerializer):
    portal_credentials = PortalCredentialSerializer(many=True, read_only=True)
    bid_count = serializers.SerializerMethodField()

    class Meta:
        model = Client
        fields = ['id', 'name', 'shortcode', 'bid_count', 'portal_credentials'] + CLIENT_INFO_FIELDS

    def get_bid_count(self, obj):
        return obj.clientbid_set.count()


class BidOpportunitySerializer(serializers.ModelSerializer):
    client_bids = ClientBidSerializer(many=True, read_only=True)

    class Meta:
        model = BidOpportunity
        fields = [
            'id', 'agency', 'title', 'solicitation_number', 'state',
            'due_date', 'bid_link', 'category', 'source_date',
            'pre_bid_info', 'qa_notes', 'last_synced',
            'created_at', 'updated_at', 'client_bids',
        ]
        read_only_fields = ['id', 'source_date', 'last_synced', 'created_at', 'updated_at']
