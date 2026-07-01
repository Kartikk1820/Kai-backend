from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    Client, BidOpportunity, ClientBid, BidAssignment, PortalCredential,
    BidOpportunityAttachment, ClientBidProposalFile,
)

User = get_user_model()


CLIENT_INFO_FIELDS = [
    'owner_name', 'incorporation_date', 'state_of_incorporation', 'corporation_type',
    'fein', 'duns', 'cage_code', 'everify_no', 'website',
    'address', 'phone', 'email', 'fax', 'notes',
]


class ClientSerializer(serializers.ModelSerializer):
    linked_user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='linked_user',
        write_only=True, required=False, allow_null=True,
    )

    class Meta:
        model = Client
        fields = ['id', 'name', 'shortcode', 'linked_user_id'] + CLIENT_INFO_FIELDS


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


class BidOpportunityAttachmentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = BidOpportunityAttachment
        fields = ['id', 'name', 'file', 'file_url', 'link', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at', 'file_url']

    def get_file_url(self, obj):
        if not obj.file:
            return None
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.file.url)
        return obj.file.url


class ClientBidProposalFileSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = ClientBidProposalFile
        fields = ['id', 'name', 'file', 'file_url', 'link', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at', 'file_url']

    def get_file_url(self, obj):
        if not obj.file:
            return None
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.file.url)
        return obj.file.url


class PortalCredentialSerializer(serializers.ModelSerializer):
    class Meta:
        model = PortalCredential
        fields = [
            'id', 'client_bid_id', 'state', 'agency', 'portal_name',
            'username', 'password', 'link', 'notes', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ClientBidSerializer(serializers.ModelSerializer):
    client = ClientSerializer(read_only=True)
    assignments = BidAssignmentSerializer(many=True, read_only=True)
    proposal_files = ClientBidProposalFileSerializer(many=True, read_only=True)
    portal_credentials = PortalCredentialSerializer(many=True, read_only=True)
    opportunity_title = serializers.CharField(source='opportunity.title', read_only=True)
    opportunity_agency = serializers.CharField(source='opportunity.agency', read_only=True)
    opportunity_state = serializers.CharField(source='opportunity.state', read_only=True)
    opportunity_due_date = serializers.DateTimeField(source='opportunity.due_date', read_only=True)
    opportunity_status = serializers.CharField(source='opportunity.status', read_only=True)
    contract_value = serializers.DecimalField(max_digits=14, decimal_places=2, required=False, allow_null=True)

    client_id = serializers.PrimaryKeyRelatedField(
        queryset=Client.objects.all(), source='client',
        write_only=True, required=False, allow_null=True
    )

    class Meta:
        model = ClientBid
        fields = [
            'id', 'opportunity_id', 'client', 'kc_brand', 'status',
            'portal_username', 'portal_password',
            'portal_credentials',
            'assignments', 'proposal_files',
            'internal_deadline', 'submission_method',
            'date_of_review', 'comments', 'contract_value',
            'created_at', 'updated_at',
            'client_id',
            'opportunity_title', 'opportunity_agency', 'opportunity_state',
            'opportunity_due_date', 'opportunity_status',
        ]
        read_only_fields = ['id', 'opportunity_id', 'created_at', 'updated_at']

    def validate(self, data):
        new_status = data.get('status')
        if new_status is None and self.instance:
            new_status = self.instance.status

        new_comments = data.get('comments')
        if new_comments is None and self.instance:
            new_comments = self.instance.comments

        if new_status in ('no_go', 'unsubmitted') and not (new_comments or '').strip():
            raise serializers.ValidationError(
                {'comments': 'A comment is required when status is No Go or Unsubmitted.'}
            )
        return data


# Slim serializer for bids nested inside ClientDetail (avoids heavy nesting)
class ClientBidSummarySerializer(serializers.ModelSerializer):
    portal_credentials = PortalCredentialSerializer(many=True, read_only=True)
    opportunity_title = serializers.CharField(source='opportunity.title', read_only=True)
    opportunity_agency = serializers.CharField(source='opportunity.agency', read_only=True)
    opportunity_due_date = serializers.DateTimeField(source='opportunity.due_date', read_only=True)
    opportunity_status = serializers.CharField(source='opportunity.status', read_only=True)
    opportunity_solicitation = serializers.CharField(source='opportunity.solicitation_number', read_only=True)

    class Meta:
        model = ClientBid
        fields = [
            'id', 'opportunity_id', 'opportunity_title', 'opportunity_agency',
            'opportunity_due_date', 'opportunity_status', 'opportunity_solicitation',
            'kc_brand', 'status', 'portal_credentials', 'created_at',
        ]
        read_only_fields = fields


class ClientDetailSerializer(serializers.ModelSerializer):
    portal_credentials = PortalCredentialSerializer(many=True, read_only=True)
    client_bids = ClientBidSummarySerializer(many=True, read_only=True, source='clientbid_set')
    bid_count = serializers.SerializerMethodField()
    linked_user = UserBidSerializer(read_only=True)

    class Meta:
        model = Client
        fields = [
            'id', 'name', 'shortcode', 'bid_count',
            'linked_user', 'portal_credentials', 'client_bids',
        ] + CLIENT_INFO_FIELDS

    def get_bid_count(self, obj):
        return obj.clientbid_set.count()


class BidOpportunitySerializer(serializers.ModelSerializer):
    client_bids = ClientBidSerializer(many=True, read_only=True)
    oc_attachments = BidOpportunityAttachmentSerializer(many=True, read_only=True)
    prewriter = UserBidSerializer(read_only=True)
    prewriter_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='prewriter',
        write_only=True, required=False, allow_null=True
    )

    class Meta:
        model = BidOpportunity
        fields = [
            'id', 'agency', 'title', 'solicitation_number', 'state',
            'due_date', 'bid_link', 'category', 'source_date',
            'pre_bid_info', 'qa_notes', 'last_synced',
            'poc', 'award_date', 'prewriter', 'prewriter_id',
            'status', 'cancellation_reason',
            'oc_attachments',
            'created_at', 'updated_at', 'client_bids',
        ]
        read_only_fields = ['id', 'source_date', 'last_synced', 'created_at', 'updated_at']

    def validate(self, data):
        new_status = data.get('status')
        if new_status is None:
            return data

        instance = self.instance
        old_status = instance.status if instance else 'draft'

        # Only validate on actual status change
        if new_status == old_status:
            return data

        if new_status == 'cancelled':
            reason = data.get('cancellation_reason') or (instance.cancellation_reason if instance else '')
            if not (reason or '').strip():
                raise serializers.ValidationError(
                    {'cancellation_reason': 'A cancellation reason is required.'}
                )

        return data
