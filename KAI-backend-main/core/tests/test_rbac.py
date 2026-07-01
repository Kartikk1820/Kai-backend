"""
RBAC system tests.

Cover:
  - Permission catalog integrity (keys, catalog, role bundles)
  - effective_permissions() logic (roles, extra grants, revokes, admin short-circuit)
  - has_perm_key() method
  - HasPermissionKey DRF permission class (200 vs 403)
  - seed_rbac command correctness
  - /auth/me/ returns correct permissions payload

Run: pytest core/tests/test_rbac.py
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient, APIRequestFactory, force_authenticate
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from core.models import Role, UserRole
from core.permissions import HasPermissionKey, HasAnyPermissionKey
from core.permissions_catalog import (
    ALL_KEYS, CATALOG, ROLE_BUNDLES,
    TASK_CREATE, TASK_VIEW_ALL,
    HR_RUN_PAYROLL,
    USER_CREATE, RBAC_MANAGE,
    BID_VIEW_OPPORTUNITY, BID_CREATE_OPPORTUNITY, BID_UPDATE_OPPORTUNITY, BID_DELETE_OPPORTUNITY,
    BID_VIEW_BID, BID_CREATE_BID, BID_UPDATE_BID, BID_DELETE_BID,
)

User = get_user_model()
pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def manager_role():
    return Role.objects.create(
        name='Manager',
        permission_keys=list(ROLE_BUNDLES['Manager']),
        is_system=True,
    )


@pytest.fixture
def hr_role():
    return Role.objects.create(
        name='HR Manager',
        permission_keys=list(ROLE_BUNDLES['HR Manager']),
        is_system=True,
    )


@pytest.fixture
def employee(db):
    return User.objects.create_user(
        'employee@test.local', 'pass', user_type='Employee', must_change_password=False
    )


@pytest.fixture
def employee_with_role(db):
    """Employee with the seeded Employee role (bid read-only)."""
    from django.core.management import call_command
    call_command('seed_rbac', verbosity=0)
    role = Role.objects.get(name='Employee')
    u = User.objects.create_user(
        'emp_role@test.local', 'pass', user_type='Employee', must_change_password=False
    )
    UserRole.objects.create(user=u, role=role)
    return u


@pytest.fixture
def manager_user(db, manager_role):
    u = User.objects.create_user(
        'manager@test.local', 'pass', user_type='Manager', must_change_password=False
    )
    UserRole.objects.create(user=u, role=manager_role)
    return u


@pytest.fixture
def hr_user(db, hr_role):
    u = User.objects.create_user(
        'hr@test.local', 'pass', user_type='Employee', must_change_password=False
    )
    UserRole.objects.create(user=u, role=hr_role)
    return u


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        'admin@test.local', 'pass', user_type='Admin',
        is_superuser=False, must_change_password=False
    )


@pytest.fixture
def superuser(db):
    return User.objects.create_superuser('super@test.local', 'pass')


# ---------------------------------------------------------------------------
# 1. Catalog integrity
# ---------------------------------------------------------------------------

class TestCatalogIntegrity:
    def test_all_keys_non_empty(self):
        assert len(ALL_KEYS) > 0

    def test_no_duplicate_keys(self):
        assert len(ALL_KEYS) == len(set(ALL_KEYS))

    def test_catalog_keys_match_all_keys(self):
        catalog_keys = [key for group in CATALOG.values() for (key, _) in group]
        assert sorted(catalog_keys) == sorted(ALL_KEYS)

    def test_role_bundle_keys_are_valid(self):
        all_set = set(ALL_KEYS)
        for role_name, keys in ROLE_BUNDLES.items():
            invalid = set(keys) - all_set
            assert not invalid, f"Role '{role_name}' has unknown keys: {invalid}"

    def test_admin_bundle_is_all_keys(self):
        assert set(ROLE_BUNDLES['Admin']) == set(ALL_KEYS)

    def test_employee_bundle_has_only_read_perms(self):
        from core.permissions_catalog import BID_VIEW_OPPORTUNITY, BID_VIEW_BID
        assert set(ROLE_BUNDLES['Employee']) == {BID_VIEW_OPPORTUNITY, BID_VIEW_BID}


# ---------------------------------------------------------------------------
# 2. effective_permissions() logic
# ---------------------------------------------------------------------------

class TestEffectivePermissions:
    def test_employee_no_roles_gets_empty(self, employee):
        # employee fixture has no UserRole assigned — effective perms from roles only = empty
        assert employee.effective_permissions() == set()

    def test_manager_gets_role_perms(self, manager_user):
        perms = manager_user.effective_permissions()
        assert TASK_CREATE in perms
        assert TASK_VIEW_ALL in perms
        # payroll perm should NOT be there
        assert HR_RUN_PAYROLL not in perms

    def test_hr_user_gets_hr_perms(self, hr_user):
        assert HR_RUN_PAYROLL in hr_user.effective_permissions()
        assert TASK_CREATE not in hr_user.effective_permissions()

    def test_admin_user_type_gets_all(self, admin_user):
        assert admin_user.effective_permissions() == set(ALL_KEYS)

    def test_superuser_gets_all(self, superuser):
        assert superuser.effective_permissions() == set(ALL_KEYS)

    def test_extra_permissions_grant_individual_key(self, employee):
        employee.extra_permissions = [TASK_CREATE]
        employee.save()
        assert TASK_CREATE in employee.effective_permissions()

    def test_revoked_permissions_remove_key_from_role(self, manager_user):
        assert TASK_CREATE in manager_user.effective_permissions()
        manager_user.revoked_permissions = [TASK_CREATE]
        manager_user.save()
        assert TASK_CREATE not in manager_user.effective_permissions()

    def test_revoke_overrides_extra(self, employee):
        employee.extra_permissions = [TASK_CREATE]
        employee.revoked_permissions = [TASK_CREATE]
        employee.save()
        assert TASK_CREATE not in employee.effective_permissions()

    def test_multiple_roles_union(self, db, manager_role, hr_role):
        u = User.objects.create_user(
            'multi@test.local', 'pass', user_type='Manager', must_change_password=False
        )
        UserRole.objects.create(user=u, role=manager_role)
        UserRole.objects.create(user=u, role=hr_role)
        perms = u.effective_permissions()
        assert TASK_CREATE in perms       # from Manager
        assert HR_RUN_PAYROLL in perms    # from HR Manager


# ---------------------------------------------------------------------------
# 3. has_perm_key()
# ---------------------------------------------------------------------------

class TestHasPermKey:
    def test_returns_true_when_key_present(self, manager_user):
        assert manager_user.has_perm_key(TASK_CREATE) is True

    def test_returns_false_when_key_absent(self, employee):
        assert employee.has_perm_key(TASK_CREATE) is False

    def test_admin_always_true(self, admin_user):
        assert admin_user.has_perm_key(HR_RUN_PAYROLL) is True
        assert admin_user.has_perm_key(RBAC_MANAGE) is True


# ---------------------------------------------------------------------------
# 4. HasPermissionKey DRF permission class
# ---------------------------------------------------------------------------

class _ProtectedView(APIView):
    permission_classes = [IsAuthenticated, HasPermissionKey.of(TASK_CREATE)]

    def get(self, request):
        return Response({'ok': True})


class TestHasPermissionKeyClass:
    def _get(self, user):
        factory = APIRequestFactory()
        request = factory.get('/')
        force_authenticate(request, user=user)
        return _ProtectedView.as_view()(request)

    def test_user_with_key_gets_200(self, manager_user):
        resp = self._get(manager_user)
        assert resp.status_code == 200

    def test_user_without_key_gets_403(self, employee):
        resp = self._get(employee)
        assert resp.status_code == 403

    def test_admin_gets_200(self, admin_user):
        resp = self._get(admin_user)
        assert resp.status_code == 200

    def test_unauthenticated_gets_401(self, db):
        factory = APIRequestFactory()
        request = factory.get('/')
        resp = _ProtectedView.as_view()(request)
        assert resp.status_code in (401, 403)


class TestHasAnyPermissionKeyClass:
    def _make_view(self, *keys):
        class V(APIView):
            permission_classes = [IsAuthenticated, HasAnyPermissionKey.of(*keys)]
            def get(self, request):
                return Response({'ok': True})
        return V.as_view()

    def _call(self, view_fn, user):
        factory = APIRequestFactory()
        request = factory.get('/')
        force_authenticate(request, user=user)
        return view_fn(request)

    def test_first_key_sufficient(self, manager_user):
        view = self._make_view(TASK_CREATE, HR_RUN_PAYROLL)
        assert self._call(view, manager_user).status_code == 200

    def test_second_key_sufficient(self, hr_user):
        view = self._make_view(TASK_CREATE, HR_RUN_PAYROLL)
        assert self._call(view, hr_user).status_code == 200

    def test_none_of_keys_gives_403(self, employee):
        view = self._make_view(TASK_CREATE, HR_RUN_PAYROLL)
        assert self._call(view, employee).status_code == 403


# ---------------------------------------------------------------------------
# 5. Bid-specific permission keys
# ---------------------------------------------------------------------------

class TestBidPermissions:
    """Verify bid permission keys exist in catalog and role bundles are correct."""

    def test_bid_keys_in_catalog(self):
        bid_keys = [BID_VIEW_OPPORTUNITY, BID_CREATE_OPPORTUNITY, BID_UPDATE_OPPORTUNITY, BID_DELETE_OPPORTUNITY,
                    BID_VIEW_BID, BID_CREATE_BID, BID_UPDATE_BID, BID_DELETE_BID]
        for key in bid_keys:
            assert key in ALL_KEYS, f"{key} missing from ALL_KEYS"

    def test_bid_group_in_catalog(self):
        assert 'Bids' in CATALOG
        catalog_keys = [k for k, _ in CATALOG['Bids']]
        assert BID_VIEW_OPPORTUNITY in catalog_keys
        assert BID_CREATE_OPPORTUNITY in catalog_keys
        assert BID_UPDATE_OPPORTUNITY in catalog_keys
        assert BID_DELETE_OPPORTUNITY in catalog_keys
        assert BID_VIEW_BID in catalog_keys
        assert BID_CREATE_BID in catalog_keys
        assert BID_UPDATE_BID in catalog_keys
        assert BID_DELETE_BID in catalog_keys

    def test_employee_role_bundle_has_read_only(self):
        emp_bundle = set(ROLE_BUNDLES['Employee'])
        assert BID_VIEW_OPPORTUNITY in emp_bundle
        assert BID_VIEW_BID in emp_bundle
        # must NOT have write perms
        assert BID_CREATE_OPPORTUNITY not in emp_bundle
        assert BID_UPDATE_OPPORTUNITY not in emp_bundle
        assert BID_DELETE_OPPORTUNITY not in emp_bundle
        assert BID_CREATE_BID not in emp_bundle
        assert BID_UPDATE_BID not in emp_bundle
        assert BID_DELETE_BID not in emp_bundle

    def test_manager_role_bundle_has_full_bid_access(self):
        mgr_bundle = set(ROLE_BUNDLES['Manager'])
        for key in [BID_VIEW_OPPORTUNITY, BID_CREATE_OPPORTUNITY, BID_UPDATE_OPPORTUNITY, BID_DELETE_OPPORTUNITY,
                    BID_VIEW_BID, BID_CREATE_BID, BID_UPDATE_BID, BID_DELETE_BID]:
            assert key in mgr_bundle, f"Manager missing {key}"

    def test_hr_manager_role_bundle_has_read_only(self):
        hr_bundle = set(ROLE_BUNDLES['HR Manager'])
        assert BID_VIEW_OPPORTUNITY in hr_bundle
        assert BID_VIEW_BID in hr_bundle
        assert BID_CREATE_OPPORTUNITY not in hr_bundle
        assert BID_UPDATE_BID not in hr_bundle

    def test_employee_with_role_can_view_but_not_create(self, employee_with_role):
        assert employee_with_role.has_perm_key(BID_VIEW_OPPORTUNITY)
        assert employee_with_role.has_perm_key(BID_VIEW_BID)
        assert not employee_with_role.has_perm_key(BID_CREATE_OPPORTUNITY)
        assert not employee_with_role.has_perm_key(BID_UPDATE_BID)
        assert not employee_with_role.has_perm_key(BID_DELETE_OPPORTUNITY)

    def test_manager_with_role_has_full_bid_access(self, manager_user):
        for key in [BID_VIEW_OPPORTUNITY, BID_CREATE_OPPORTUNITY, BID_UPDATE_OPPORTUNITY, BID_DELETE_OPPORTUNITY,
                    BID_VIEW_BID, BID_CREATE_BID, BID_UPDATE_BID, BID_DELETE_BID]:
            assert manager_user.has_perm_key(key), f"manager missing {key}"

    def test_hr_user_can_view_bids_but_not_create(self, hr_user):
        assert hr_user.has_perm_key(BID_VIEW_OPPORTUNITY)
        assert hr_user.has_perm_key(BID_VIEW_BID)
        assert not hr_user.has_perm_key(BID_CREATE_OPPORTUNITY)
        assert not hr_user.has_perm_key(BID_UPDATE_BID)


# ---------------------------------------------------------------------------
# 6. seed_rbac command
# ---------------------------------------------------------------------------

class TestSeedRbac:
    def test_seed_creates_system_roles(self, db):
        from django.core.management import call_command
        call_command('seed_rbac', verbosity=0)
        for role_name, keys in ROLE_BUNDLES.items():
            role = Role.objects.get(name=role_name)
            assert role.is_system is True
            assert set(role.permission_keys) == set(keys)

    def test_seed_is_idempotent(self, db):
        from django.core.management import call_command
        call_command('seed_rbac', verbosity=0)
        call_command('seed_rbac', verbosity=0)
        assert Role.objects.filter(name='Admin').count() == 1

    def test_seeded_manager_role_has_task_create(self, db):
        from django.core.management import call_command
        call_command('seed_rbac', verbosity=0)
        role = Role.objects.get(name='Manager')
        assert TASK_CREATE in role.permission_keys

    def test_seeded_employee_role_has_bid_read_only(self, db):
        from django.core.management import call_command
        from core.permissions_catalog import BID_VIEW_OPPORTUNITY, BID_VIEW_BID
        call_command('seed_rbac', verbosity=0)
        role = Role.objects.get(name='Employee')
        assert set(role.permission_keys) == {BID_VIEW_OPPORTUNITY, BID_VIEW_BID}


# ---------------------------------------------------------------------------
# 7. /auth/me/ returns permissions in response
# ---------------------------------------------------------------------------

class TestMeEndpointPermissions:
    def test_me_returns_permissions_list(self, manager_user):
        client = APIClient()
        client.force_authenticate(user=manager_user)
        resp = client.get('/auth/me/')
        assert resp.status_code == 200
        data = resp.json().get('data') or resp.json()
        perms = data.get('permissions', [])
        assert isinstance(perms, list)
        assert TASK_CREATE in perms

    def test_me_employee_gets_empty_permissions(self, employee):
        client = APIClient()
        client.force_authenticate(user=employee)
        resp = client.get('/auth/me/')
        assert resp.status_code == 200
        data = resp.json().get('data') or resp.json()
        assert data.get('permissions', []) == []

    def test_me_admin_gets_all_keys(self, admin_user):
        client = APIClient()
        client.force_authenticate(user=admin_user)
        resp = client.get('/auth/me/')
        assert resp.status_code == 200
        data = resp.json().get('data') or resp.json()
        perms = set(data.get('permissions', []))
        assert set(ALL_KEYS).issubset(perms)
