import calendar as _calendar
import pytest
from datetime import date
from decimal import Decimal
from django.contrib.auth import get_user_model
from hrms.models import (
    LeaveRequest, LeaveBalance, Attendance, CompensationVersion, PayrollRecord, Incentive,
)
from hrms.services import LeaveService, PayrollService, IncentiveService
from hrms.utils import amount_to_words_inr

User = get_user_model()
pytestmark = pytest.mark.django_db


def _fill_working_days(emp, year, month, fill_status='present'):
    """Create Attendance rows for every Mon-Fri not already covered (tests have no entity WeeklyOffRule)."""
    days_in_month = _calendar.monthrange(year, month)[1]
    existing = set(
        Attendance.objects.filter(employee=emp, date__year=year, date__month=month)
        .values_list('date', flat=True)
    )
    for day in range(1, days_in_month + 1):
        d = date(year, month, day)
        if d.weekday() not in {5, 6} and d not in existing:
            Attendance.objects.create(employee=emp, date=d, status=fill_status)


@pytest.fixture
def admin(db):
    return User.objects.create_user('a@h.test', 'pass12345', user_type='Admin', must_change_password=False)


@pytest.fixture
def emp(db, admin):
    return User.objects.create_user('e@h.test', 'pass12345', user_type='Employee', manager=admin)


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
        basic_salary=Decimal('30000'),
    )
    _fill_working_days(emp, 2026, 5)
    PayrollService.run_salary(5, 2026, user=admin)
    PayrollService.run_salary(5, 2026, user=admin)
    assert PayrollRecord.objects.filter(employee=emp, month=5, year=2026, slip_type='salary').count() == 1


def test_payroll_skips_employee_with_unmarked_attendance(emp, admin):
    """An unmarked row on a working day blocks payroll even if all other days are covered."""
    CompensationVersion.objects.create(
        employee=emp, effective_from=date(2026, 1, 1),
        basic_salary=Decimal('30000'),
    )
    # May 11 is a Monday — a real working day
    Attendance.objects.create(employee=emp, date=date(2026, 5, 11), status='unmarked')
    _fill_working_days(emp, 2026, 5)  # fills remaining working days as present
    run = PayrollService.run_salary(5, 2026, user=admin)
    assert PayrollRecord.objects.filter(employee=emp, month=5, year=2026).count() == 0
    assert any('unmarked' in e['error'] for e in run.errors if e['employee'] == emp.id)


def test_payroll_skips_employee_with_missing_attendance_rows(emp, admin):
    """Employee with no Attendance rows at all must be skipped — the real bug this gate fixes."""
    CompensationVersion.objects.create(
        employee=emp, effective_from=date(2026, 1, 1),
        basic_salary=Decimal('30000'),
    )
    # Deliberately create zero Attendance rows for the period
    run = PayrollService.run_salary(5, 2026, user=admin)
    assert PayrollRecord.objects.filter(employee=emp, month=5, year=2026).count() == 0
    assert any('no attendance record' in e['error'] for e in run.errors if e['employee'] == emp.id)


def test_payroll_lop_deduction(emp, admin):
    """LOP days reduce net below gross."""
    CompensationVersion.objects.create(
        employee=emp, effective_from=date(2026, 1, 1),
        basic_salary=Decimal('30000'),
    )
    # May 11 is a Monday (working day)
    Attendance.objects.create(employee=emp, date=date(2026, 5, 11), status='lop')
    _fill_working_days(emp, 2026, 5)  # covers all remaining working days
    PayrollService.run_salary(5, 2026, user=admin)
    rec = PayrollRecord.objects.get(employee=emp, month=5, year=2026, slip_type='salary')
    assert rec.lop_days == Decimal('1')
    assert rec.lop_deduction > Decimal('0')
    assert rec.net_amount < rec.gross_earnings


def test_payroll_attendance_snapshot(emp, admin):
    """Attendance breakdown fields are snapshotted on PayrollRecord."""
    CompensationVersion.objects.create(
        employee=emp, effective_from=date(2026, 1, 1),
        basic_salary=Decimal('30000'),
    )
    Attendance.objects.create(employee=emp, date=date(2026, 5, 5), status='present')
    Attendance.objects.create(employee=emp, date=date(2026, 5, 6), status='sick_leave')
    Attendance.objects.create(employee=emp, date=date(2026, 5, 7), status='weekly_off')
    Attendance.objects.create(employee=emp, date=date(2026, 5, 11), status='holiday')
    _fill_working_days(emp, 2026, 5)  # covers remaining Mon-Fri not yet assigned
    PayrollService.run_salary(5, 2026, user=admin)
    rec = PayrollRecord.objects.get(employee=emp, month=5, year=2026, slip_type='salary')
    # May 5 (present) + 17 days filled by _fill_working_days = 18 present
    assert rec.days_present == Decimal('18')
    assert rec.paid_leave_days == Decimal('1')  # May 6 sick_leave
    assert rec.weekly_offs == 1                  # May 7 weekly_off
    assert rec.public_holidays == 1              # May 11 holiday
    assert rec.total_working_days > 0


def test_amount_to_words_inr():
    assert amount_to_words_inr(0) == 'Zero Rupees'
    assert amount_to_words_inr(100000) == 'One Lakh Rupees'
    assert amount_to_words_inr(1500000) == 'Fifteen Lakh Rupees'
    assert amount_to_words_inr(41695) == 'Forty One Thousand Six Hundred Ninety Five Rupees'
    assert amount_to_words_inr(10000000) == 'One Crore Rupees'
    assert amount_to_words_inr(1234567) == 'Twelve Lakh Thirty Four Thousand Five Hundred Sixty Seven Rupees'


def test_incentive_send(emp, admin):
    inc = Incentive.objects.create(employee=emp, amount=Decimal('5000'), reason='b', month=6, year=2026)
    IncentiveService.send(inc.id, user=admin)
    inc.refresh_from_db()
    assert inc.status == 'sent'
    assert PayrollRecord.objects.filter(employee=emp, slip_type='incentive').count() == 1
