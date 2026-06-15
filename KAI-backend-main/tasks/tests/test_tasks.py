import pytest
from django.contrib.auth import get_user_model
from tasks.models import Task
from tasks.services import TaskService
from core.models import AuditLog
from rest_framework.exceptions import ValidationError, PermissionDenied

User = get_user_model()
pytestmark = pytest.mark.django_db


@pytest.fixture
def admin(db):
    return User.objects.create_user('admin@t.test', 'pass12345', role='Admin', must_change_password=False)


@pytest.fixture
def emp(db, admin):
    return User.objects.create_user('emp@t.test', 'pass12345', role='Employee', manager=admin)


def test_key_generation(emp):
    t = Task.objects.create(title='A', reporter=emp, created_by=emp)
    assert t.key.startswith('KAI-')


def test_legal_transition(emp):
    t = Task.objects.create(title='A', reporter=emp, created_by=emp, assignee=emp)
    TaskService.transition(t.id, emp, action='start')
    assert Task.objects.get(id=t.id).status == 'in_progress'


def test_illegal_employee_jump_blocked(emp):
    t = Task.objects.create(title='A', reporter=emp, created_by=emp, assignee=emp)
    TaskService.transition(t.id, emp, action='start')
    with pytest.raises(ValidationError):
        TaskService.transition(t.id, emp, target='done')


def test_block_requires_reason(emp):
    t = Task.objects.create(title='A', reporter=emp, created_by=emp, assignee=emp)
    with pytest.raises(ValidationError):
        TaskService.transition(t.id, emp, action='block')


def test_admin_override(emp, admin):
    t = Task.objects.create(title='A', reporter=emp, created_by=emp, assignee=emp)
    TaskService.transition(t.id, admin, target='done')
    assert Task.objects.get(id=t.id).status == 'done'


def test_audit_written(emp):
    t = Task.objects.create(title='A', reporter=emp, created_by=emp, assignee=emp)
    TaskService.transition(t.id, emp, action='start')
    assert AuditLog.objects.filter(model_name='Task', object_id=str(t.id)).exists()
