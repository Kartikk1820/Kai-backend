from rest_framework.views import APIView
from rest_framework.generics import RetrieveAPIView, ListCreateAPIView, RetrieveUpdateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.views import (
    TokenObtainPairView, TokenRefreshView, TokenBlacklistView,
)
from rest_framework_simplejwt.serializers import TokenRefreshSerializer, TokenBlacklistSerializer
from drf_spectacular.utils import extend_schema, OpenApiResponse
from django.contrib.auth import get_user_model
from django.utils.crypto import get_random_string

from core.permissions import HasPermissionKey
from core.permissions_catalog import USER_CREATE, USER_RESET_PASSWORD, RBAC_MANAGE
from core.services import write_audit
from core.models import Role, UserTypePermissions
from .serializers import (
    CustomTokenObtainPairSerializer, MeSerializer, ChangePasswordSerializer,
    AdminUserSerializer, RoleSerializer, CustomTokenRefreshSerializer,
    UserMiniSerializer, ProfileUpdateSerializer, PositionSerializer,
)
from .models import Position

User = get_user_model()


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

    @extend_schema(summary="Login", description="Email + password → access/refresh tokens and the user profile.")
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class CustomTokenRefreshView(TokenRefreshView):
    serializer_class = CustomTokenRefreshSerializer

    @extend_schema(summary="Refresh token", request=CustomTokenRefreshSerializer, responses={200: CustomTokenRefreshSerializer})
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class CustomTokenBlacklistView(TokenBlacklistView):
    @extend_schema(summary="Logout", request=TokenBlacklistSerializer,
                   responses={200: OpenApiResponse(description="Token blacklisted")})
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class UserMeView(RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = MeSerializer

    @extend_schema(summary="Current user", description="Profile + effective permissions for the SPA.")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_object(self):
        return self.request.user

    @extend_schema(summary="Update own profile", request=ProfileUpdateSerializer)
    def patch(self, request, *args, **kwargs):
        ser = ProfileUpdateSerializer(request.user, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        write_audit(actor=request.user, model_name='User', object_id=request.user.id,
                    action='profile_update', new_state='updated', request=request)
        return Response(MeSerializer(request.user, context={'request': request}).data)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(summary="Change own password", request=ChangePasswordSerializer)
    def post(self, request):
        ser = ChangePasswordSerializer(data=request.data, context={'request': request})
        ser.is_valid(raise_exception=True)
        user = request.user
        # If not a forced change, verify the current password.
        if not user.must_change_password:
            current = ser.validated_data.get('current_password') or ''
            if not user.check_password(current):
                return Response({'current_password': ['Incorrect password.']},
                                status=status.HTTP_400_BAD_REQUEST)
        user.set_password(ser.validated_data['new_password'])
        user.must_change_password = False
        user.save(update_fields=['password', 'must_change_password'])
        write_audit(actor=user, model_name='User', object_id=user.id,
                    action='password_change', new_state='changed', request=request)
        return Response({'detail': 'Password updated.'})


# ---------------- Public user list (for peer-to-peer features) ----------------

class UserListView(APIView):
    """Any authenticated user can list colleagues for document sharing, etc."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = User.objects.exclude(user_type='Client').exclude(id=request.user.id).order_by('first_name', 'email')
        return Response(UserMiniSerializer(qs, many=True).data)


# ---------------- Admin: users & roles ----------------

class AdminUserListCreateView(ListCreateAPIView):
    pagination_class = None
    serializer_class = AdminUserSerializer
    permission_classes = [HasPermissionKey.of(USER_CREATE)]
    queryset = User.objects.exclude(user_type='Client').order_by('id')

    def create(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user = ser.save()
        write_audit(actor=request.user, model_name='User', object_id=user.id,
                    action='created', new_state='active', request=request)
        data = ser.data
        # surface the initial password once so the admin can share it
        data['initial_password'] = getattr(ser, '_plain_password', None)
        return Response(data, status=status.HTTP_201_CREATED)


class AdminUserDetailView(RetrieveUpdateAPIView):
    serializer_class = AdminUserSerializer
    permission_classes = [HasPermissionKey.of(USER_CREATE)]
    queryset = User.objects.all()
    http_method_names = ['get', 'patch']


class AdminResetPasswordView(APIView):
    permission_classes = [HasPermissionKey.of(USER_RESET_PASSWORD)]

    @extend_schema(summary="Admin reset password",
                   description="Sets a new password and forces a one-time change on next login.")
    def post(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        new_password = request.data.get('password') or get_random_string(12)
        user.set_password(new_password)
        user.must_change_password = True
        user.save(update_fields=['password', 'must_change_password'])
        write_audit(actor=request.user, model_name='User', object_id=user.id,
                    action='password_reset', new_state='reset', request=request)
        return Response({'detail': 'Password reset.', 'initial_password': new_password})


class RoleListCreateView(ListCreateAPIView):
    pagination_class = None
    serializer_class = RoleSerializer
    permission_classes = [HasPermissionKey.of(RBAC_MANAGE)]
    queryset = Role.objects.all()


class RoleDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = RoleSerializer
    permission_classes = [HasPermissionKey.of(RBAC_MANAGE)]
    queryset = Role.objects.all()
    http_method_names = ['get', 'patch', 'delete']

    def perform_destroy(self, instance):
        from rest_framework.exceptions import ValidationError
        if instance.is_system:
            raise ValidationError("Cannot delete a system role.")
        instance.delete()


class PermissionCatalogView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(summary="Permission catalog", description="Grouped list of all permission keys.")
    def get(self, request):
        from core.permissions_catalog import CATALOG
        data = {group: [{'key': k, 'label': lbl} for (k, lbl) in items]
                for group, items in CATALOG.items()}
        return Response(data)


class UserTypePermissionsView(APIView):
    """GET all user_type permission maps; PATCH a specific user_type."""
    permission_classes = [HasPermissionKey.of(RBAC_MANAGE)]

    def get(self, request):
        items = UserTypePermissions.objects.all()
        return Response({item.user_type: item.permission_keys for item in items})

    def patch(self, request, user_type):
        from core.permissions_catalog import ALL_KEYS
        keys = request.data.get('permission_keys', [])
        invalid = [k for k in keys if k not in ALL_KEYS]
        if invalid:
            return Response({'error': f'Unknown permission keys: {invalid}'}, status=400)
        obj, _ = UserTypePermissions.objects.get_or_create(user_type=user_type)
        obj.permission_keys = keys
        obj.save()
        write_audit(actor=request.user, model_name='UserTypePermissions',
                    object_id=user_type, action='updated', request=request)
        return Response({'user_type': obj.user_type, 'permission_keys': obj.permission_keys})


class PositionListCreateView(ListCreateAPIView):
    permission_classes = [HasPermissionKey.of(RBAC_MANAGE)]
    serializer_class = PositionSerializer
    queryset = Position.objects.all()


class PositionDetailView(RetrieveUpdateDestroyAPIView):
    permission_classes = [HasPermissionKey.of(RBAC_MANAGE)]
    serializer_class = PositionSerializer
    queryset = Position.objects.all()
    http_method_names = ['get', 'patch', 'delete']
