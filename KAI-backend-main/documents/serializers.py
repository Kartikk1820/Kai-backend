from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import SharedDocument, DocumentRequest

User = get_user_model()


class UserMiniSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    avatar_initials = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'email', 'full_name', 'avatar_initials']


class SharedDocumentSerializer(serializers.ModelSerializer):
    sender = UserMiniSerializer(read_only=True)
    recipient = UserMiniSerializer(read_only=True)
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = SharedDocument
        fields = [
            'id', 'sender', 'recipient', 'filename', 'size', 'content_type',
            'message', 'is_downloaded', 'file_url', 'fulfills_request_id', 'created_at',
        ]

    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return None


class SendDocumentSerializer(serializers.Serializer):
    recipient_id = serializers.IntegerField()
    file = serializers.FileField()
    message = serializers.CharField(required=False, allow_blank=True, default='')
    fulfills_request_id = serializers.IntegerField(required=False, allow_null=True, default=None)

    def validate_recipient_id(self, value):
        if not User.objects.filter(id=value).exists():
            raise serializers.ValidationError("Recipient not found.")
        return value


class DocumentRequestSerializer(serializers.ModelSerializer):
    requester = UserMiniSerializer(read_only=True)
    target = UserMiniSerializer(read_only=True)
    fulfilled_document = SharedDocumentSerializer(read_only=True)

    class Meta:
        model = DocumentRequest
        fields = [
            'id', 'requester', 'target', 'document_type', 'message',
            'status', 'fulfilled_document', 'created_at', 'updated_at',
        ]


class CreateDocumentRequestSerializer(serializers.Serializer):
    target_id = serializers.IntegerField()
    document_type = serializers.CharField(max_length=255)
    message = serializers.CharField(required=False, allow_blank=True, default='')

    def validate_target_id(self, value):
        if not User.objects.filter(id=value).exists():
            raise serializers.ValidationError("Target user not found.")
        return value
