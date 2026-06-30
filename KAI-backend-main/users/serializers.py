from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils.crypto import get_random_string
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from core.models import Role, UserRole
from .models import Position, Entity

User = get_user_model()


class PositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Position
        fields = ['id', 'name', 'description', 'role_ids']


class RoleSerializer(serializers.ModelSerializer):
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = ['id', 'name', 'description', 'permission_keys', 'is_system', 'member_count']
        read_only_fields = ['is_system', 'member_count']

    def get_member_count(self, obj):
        return obj.members.count()


class UserMiniSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    avatar_initials = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'email', 'full_name', 'avatar_initials', 'user_type']


class MeSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    avatar_initials = serializers.CharField(read_only=True)
    permissions = serializers.SerializerMethodField()
    roles = serializers.SerializerMethodField()
    is_manager = serializers.SerializerMethodField()
    # entity = name string (backward compat); entity_id = FK integer
    entity = serializers.SerializerMethodField()
    entity_id = serializers.PrimaryKeyRelatedField(source='entity', read_only=True)
    designation = serializers.SerializerMethodField()
    designation_id = serializers.PrimaryKeyRelatedField(source='designation', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name', 'avatar_initials',
            'user_type', 'designation', 'designation_id', 'entity', 'entity_id',
            'manager', 'phone_number',
            'must_change_password', 'is_manager', 'permissions', 'roles',
            'state', 'present_location', 'job_id',
        ]

    def get_entity(self, obj):
        return obj.entity.name if obj.entity_id else None

    def get_designation(self, obj):
        return obj.designation.name if obj.designation_id else None

    def get_permissions(self, obj):
        return sorted(obj.effective_permissions())

    def get_roles(self, obj):
        return list(obj.user_roles.values_list('role__name', flat=True))

    def get_is_manager(self, obj):
        return obj.subordinates.exists()


class ProfileUpdateSerializer(serializers.ModelSerializer):
    """Fields a user is allowed to edit on their own profile."""
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone_number', 'present_location', 'state']


class AdminUserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    role_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Role.objects.all(), write_only=True, required=False
    )
    roles = serializers.SerializerMethodField()
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    # entity = name string (backward compat read); entity_id = FK write/read
    entity = serializers.SerializerMethodField()
    entity_id = serializers.PrimaryKeyRelatedField(
        queryset=Entity.objects.all(), source='entity',
        allow_null=True, required=False,
    )
    designation = serializers.SerializerMethodField()
    designation_id = serializers.PrimaryKeyRelatedField(
        queryset=Position.objects.all(), source='designation',
        allow_null=True, required=False,
    )

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name', 'user_type',
            'designation', 'designation_id', 'manager', 'entity', 'entity_id',
            'phone_number', 'date_of_joining',
            'is_active', 'must_change_password', 'password', 'role_ids', 'roles',
            'state', 'present_location', 'job_id',
        ]
        read_only_fields = ['must_change_password']

    def get_entity(self, obj):
        return obj.entity.name if obj.entity_id else None

    def get_designation(self, obj):
        return obj.designation.name if obj.designation_id else None

    def get_roles(self, obj):
        return list(obj.user_roles.values_list('role__name', flat=True))

    def create(self, validated_data):
        role_objs = validated_data.pop('role_ids', [])
        password = validated_data.pop('password', None) or get_random_string(12)
        user = User(**validated_data)
        user.must_change_password = True
        user.set_password(password)
        user.save()
        for r in role_objs:
            UserRole.objects.get_or_create(user=user, role=r)
        self._plain_password = password  # surfaced by the view for the admin to share
        return user

    def update(self, instance, validated_data):
        role_objs = validated_data.pop('role_ids', None)
        validated_data.pop('password', None)  # password changes go through reset endpoint
        for k, v in validated_data.items():
            setattr(instance, k, v)
        instance.save()
        if role_objs is not None:
            instance.user_roles.all().delete()
            for r in role_objs:
                UserRole.objects.get_or_create(user=instance, role=r)
        return instance


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    new_password = serializers.CharField(write_only=True)

    def validate_new_password(self, value):
        validate_password(value, self.context['request'].user)
        return value


from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.exceptions import InvalidToken

class CustomTokenRefreshSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken(attrs['refresh'])
        user_id = refresh.payload.get('user_id')
        pw_hash = refresh.payload.get('pw_hash')
        if user_id and pw_hash:
            try:
                user = User.objects.get(id=user_id)
                if pw_hash != user.password[-10:]:
                    raise InvalidToken('Password has changed. Please log in again.')
            except User.DoesNotExist:
                pass
        return data


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['pw_hash'] = user.password[-10:]
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data['user'] = MeSerializer(self.user).data
        return data
