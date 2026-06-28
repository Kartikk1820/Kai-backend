import pytest
from datetime import date
from decimal import Decimal
from django.contrib.auth import get_user_model
from hrms.models import (
    LeaveRequest, LeaveBalance, Attendance, CompensationVersion, PayrollRecord, Incentive,
)
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
    lr = LeaveRequest.objects.create(
        employee=emp, leave_type='sick',
        from_date=date(2026, 6, 1), to_date=date(2026, 6, 3),
        total_days=3, reason='x', status='pending',
    )
    LeaveService.approve(lr.id, admin)
    assert LeaveBalance.objects.get(employee=emp).sick_used == Decimal('3')
    # Status should now be granular sick_leave, not generic 'leave'
    assert Attendance.objects.filter(employee=emp, status='sick_leave').count() == 3


def test_leave_approval_half_day(emp, admin):
    LeaveBalance.objects.create(employee=emp)
    lr = LeaveRequest.objects.create(
        employee=emp, leave_type='casual',
        from_date=date(2026, 6, 5), to_date=date(2026, 6, 5),
        total_days=Decimal('0.5'), reason='x', status='pending',
    )
    LeaveService.approve(lr.id, admin)
    att = Attendance.objects.get(employee=emp, date=date(2026, 6, 5))
    assert att.status == 'casual_leave'
    assert att.is_half_day is True
    assert LeaveBalance.objects.get(employee=emp).casual_used == Decimal('0.5')


def test_reject_requires_reason(emp, admin):
    lr = LeaveRequest.objects.create(
        employee=emp, leave_type='sick',
        from_date=date(2026, 6, 1), to_date=date(2026, 6, 1),
        total_days=1, reason='x', status='pending',
    )
    from rest_framework.exceptions import ValidationError
    with pytest.raises(ValidationError):
        LeaveService.reject(lr.id, admin, '')


def test_payroll_skips_employee_without_compensation(emp, admin):
    """No CompensationVersion → employee goes into errors, no PayrollRecord created."""
    run = PayrollService.run_salary(5, 2026, user=admin)
    assert PayrollRecord.objects.filter(employee=emp, month=5, year=2026).count() == 0
    assert any(e['employee'] == emp.id for e in run.errors)


def test_payroll_idempotent(emp, admin):
    CompensationVersion.objects.create(
        employee=emp,
        effective_from=date(2026, 1, 1),
        monthly_base_salary=Decimal('30000'),
    )
    PayrollService.run_salary(5, 2026, user=admin)
    PayrollService.run_salary(5, 2026, user=admin)
    assert PayrollRecord.objects.filter(employee=emp, month=5, year=2026, slip_type='salary').count() == 1


def test_payroll_skips_employee_with_unmarked_attendance(emp, admin):
    CompensationVersion.objects.create(
        employee=emp, effective_from=date(2026, 1, 1),
        monthly_base_salary=Decimal('30000'),
    )
    Attendance.objects.create(employee=emp, date=date(2026, 5, 10), status='unmarked')
    run = PayrollService.run_salary(5, 2026, user=admin)
    assert PayrollRecord.objects.filter(employee=emp, month=5, year=2026).count() == 0
    assert any('unmarked' in e['error'] for e in run.errors if e['employee'] == emp.id)


def test_payroll_lop_deduction(emp, admin):
    """LOP days reduce net below gross."""
    CompensationVersion.objects.create(
        employee=emp, effective_from=date(2026, 1, 1),
        monthly_base_salary=Decimal('30000'),
    )
    Attendance.objects.create(employee=emp, date=date(2026, 5, 10), status='lop')
    PayrollService.run_salary(5, 2026, user=admin)
    rec = PayrollRecord.objects.get(employee=emp, month=5, year=2026, slip_type='salary')
    assert rec.lop_days == Decimal('1')
    assert rec.lop_deduction > Decimal('0')
    assert rec.net_amount < rec.gross_earnings


def test_incentive_send(emp, admin):
    inc = Incentive.objects.create(employee=emp, amount=Decimal('5000'), reason='b', month=6, year=2026)
    IncentiveService.send(inc.id, user=admin)
    inc.refresh_from_db()
    assert inc.status == 'sent'
    assert PayrollRecord.objects.filter(employee=emp, slip_type='incentive').count() == 1
