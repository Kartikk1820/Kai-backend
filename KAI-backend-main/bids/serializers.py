from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Client, BidOpportunity, ClientBid

User = get_user_model()


class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = ['id', 'name', 'shortcode']


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


class ClientBidSerializer(serializers.ModelSerializer):
    client = ClientSerializer(read_only=True)
    presales_person = UserBidSerializer(read_only=True)
    writer = UserBidSerializer(read_only=True)

    # Write-only FK fields
    client_id = serializers.PrimaryKeyRelatedField(
        queryset=Client.objects.all(), source='client',
        write_only=True, required=False, allow_null=True
    )
    presales_person_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='presales_person',
        write_only=True, required=False, allow_null=True
    )
    writer_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='writer',
        write_only=True, required=False, allow_null=True
    )

    class Meta:
        model = ClientBid
        fields = [
            'id', 'opportunity_id', 'client', 'kc_brand', 'status',
            'portal_username', 'portal_password',
            'presales_person', 'writer',
            'internal_deadline', 'submission_method',
            'date_of_review', 'comments',
            'created_at', 'updated_at',
            # write-only
            'client_id', 'presales_person_id', 'writer_id',
        ]
        read_only_fields = ['id', 'opportunity_id', 'created_at', 'updated_at']


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
