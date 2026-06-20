from django.urls import path
from .views import (
    CustomTokenObtainPairView, UserMeView, CustomTokenRefreshView,
    CustomTokenBlacklistView, ChangePasswordView,
    AdminUserListCreateView, AdminUserDetailView, AdminResetPasswordView,
    RoleListCreateView, RoleDetailView, PermissionCatalogView,
    UserListView,
)

urlpatterns = [
    path('login/', CustomTokenObtainPairView.as_view(), name='login'),
    path('logout/', CustomTokenBlacklistView.as_view(), name='logout'),
    path('refresh/', CustomTokenRefreshView.as_view(), name='refresh'),
    path('me/', UserMeView.as_view(), name='user-me'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('users/', UserListView.as_view(), name='user-list'),

    # Admin
    path('admin/users/', AdminUserListCreateView.as_view(), name='admin-user-list'),
    path('admin/users/<int:pk>/', AdminUserDetailView.as_view(), name='admin-user-detail'),
    path('admin/users/<int:pk>/reset-password/', AdminResetPasswordView.as_view(), name='admin-user-reset'),
    path('admin/roles/', RoleListCreateView.as_view(), name='role-list'),
    path('admin/roles/<int:pk>/', RoleDetailView.as_view(), name='role-detail'),
    path('admin/permissions/', PermissionCatalogView.as_view(), name='permission-catalog'),
]
