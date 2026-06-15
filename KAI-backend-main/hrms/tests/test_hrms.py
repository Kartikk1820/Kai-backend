import pytest
from datetime import date
from decimal import Decimal
from django.contrib.auth import get_user_model
from hrms.models import LeaveRequest, LeaveBalance, Attendance, Compensation, PayrollRecord, Incentive
from hrms.services import LeaveService, PayrollService, IncentiveService

User = get_user_model()
pytestmark = pytest.mark.django_db


@pytest.fixture
def admin(db):
    return User.objects.create_user('a@h.test', 'pass12345', role='Admin', must_change_password=False)


@pytest.fixture
def emp(db, admin):
    return User.objects.create_user('e@h.test', 'pass12345', role='Employee', manager=admin)


def test_leave_approval_decrements_balance_and_writes_attendance(emp, admin):
    LeaveBalance.objects.create(employee=emp)
    lr = LeaveRequest.objects.create(employee=emp, leave_type='sick', from_date=date(2026, 6, 1),
                                     to_date=date(2026, 6, 3), total_days=3, reason='x', status='pending')
    LeaveService.approve(lr.id, admin)
    assert LeaveBalance.objects.get(employee=emp).sick_used == 3
    assert Attendance.objects.filter(employee=emp, status='leave').count() == 3


def test_reject_requires_reason(emp, admin):
    lr = LeaveRequest.objects.create(employee=emp, leave_type='sick', from_date=date(2026, 6, 1),
                                     to_date=date(2026, 6, 1), total_days=1, reason='x', status='pending')
    from rest_framework.exceptions import ValidationError
    with pytest.raises(ValidationError):
        LeaveService.reject(lr.id, admin, '')


def test_payroll_idempotent(emp, admin):
    Compensation.objects.create(employee=emp, monthly_base_salary=Decimal('30000'))
    PayrollService.run_salary(5, 2026, user=admin)
    PayrollService.run_salary(5, 2026, user=admin)
    assert PayrollRecord.objects.filter(employee=emp, month=5, year=2026, slip_type='salary').count() == 1


def test_incentive_send(emp, admin):
    inc = Incentive.objects.create(employee=emp, amount=Decimal('5000'), reason='b', month=6, year=2026)
    IncentiveService.send(inc.id, user=admin)
    inc.refresh_from_db()
    assert inc.status == 'sent'
    assert PayrollRecord.objects.filter(employee=emp, slip_type='incentive').count() == 1
