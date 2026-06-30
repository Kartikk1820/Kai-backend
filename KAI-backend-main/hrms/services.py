"""HRMS service layer: attendance seeding, leave approval, payroll generation."""
import calendar
from datetime import timedelta, date
from decimal import Decimal, ROUND_HALF_UP
from django.db import models, transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from core.services import write_audit
from core.permissions_catalog import HR_APPROVE_LEAVE
from notifications.services import notify
from .models import (
    LeaveRequest, LeaveBalance, Attendance, CompensationVersion, PayrollRecord,
    PayrollRun, Incentive, WeeklyOffRule, WorkingCalendarEntry, ProfessionalTaxSlab,
)

# Maps LeaveRequest.leave_type → Attendance.status
LEAVE_TYPE_TO_STATUS = {
    'sick': 'sick_leave',
    'casual': 'casual_leave',
    'earned': 'earned_leave',
    'unpaid': 'lop',
}

# Statuses that count as LOP days in payroll
LOP_STATUSES = ('lop', 'absent')


def can_approve_for(user, employee):
    """Admin/HR (permission) OR employee's direct manager."""
    if user.user_type == 'Admin' or user.has_perm_key(HR_APPROVE_LEAVE):
        return True
    return employee.manager_id == user.id


def _working_days_in_month(month, year, entity):
    """Calendar days minus weekly-offs (from WeeklyOffRule) minus public holidays.
    Falls back to Sat+Sun off when entity is None or has no WeeklyOffRule configured."""
    if entity:
        off_weekdays = set(
            WeeklyOffRule.objects.filter(entity=entity).values_list('weekday', flat=True)
        )
        if not off_weekdays:
            off_weekdays = {5, 6}  # sensible default if entity has no rules yet
        holiday_dates = set(
            WorkingCalendarEntry.objects.filter(
                entity=entity, entry_type='holiday',
                date__year=year, date__month=month,
            ).values_list('date', flat=True)
        )
    else:
        off_weekdays = {5, 6}
        holiday_dates = set()

    days_in_month = calendar.monthrange(year, month)[1]
    working = 0
    for day in range(1, days_in_month + 1):
        d = date(year, month, day)
        if d.weekday() not in off_weekdays and d not in holiday_dates:
            working += 1
    return working


def _get_professional_tax(entity, gross, month_start):
    """Look up monthly PT for gross salary against entity's current slab table."""
    slab = (
        ProfessionalTaxSlab.objects
        .filter(
            entity=entity,
            effective_from__lte=month_start,
            income_from__lte=gross,
        )
        .filter(models.Q(income_to__isnull=True) | models.Q(income_to__gte=gross))
        .order_by('-effective_from', 'income_from')
        .first()
    )
    return slab.monthly_tax if slab else Decimal('0')


class AttendanceService:

    @staticmethod
    @transaction.atomic
    def seed_calendar(month, year):
        """
        Pre-create Attendance rows for holidays and weekly-offs for all active employees.
        Holidays take precedence over weekly-offs on the same date.
        Never overwrites an existing row — uses get_or_create so clock-in rows survive.
        """
        from django.contrib.auth import get_user_model
        User = get_user_model()

        from users.models import Entity
        for entity in Entity.objects.filter(is_active=True):
            employees = list(
                User.objects.filter(entity=entity, is_active=True)
                .exclude(user_type='Client')
            )
            if not employees:
                continue

            # Build per-date intent: holiday > weekly_off
            off_weekdays = set(
                WeeklyOffRule.objects.filter(entity=entity).values_list('weekday', flat=True)
            )
            holiday_map = {
                entry.date: entry.name
                for entry in WorkingCalendarEntry.objects.filter(
                    entity=entity, date__year=year, date__month=month,
                )
            }

            days_in_month = calendar.monthrange(year, month)[1]
            for day in range(1, days_in_month + 1):
                d = date(year, month, day)

                if d in holiday_map:
                    att_status = 'holiday'
                elif d.weekday() in off_weekdays:
                    att_status = 'weekly_off'
                else:
                    continue  # working day — no pre-seeded row needed

                for emp in employees:
                    Attendance.objects.get_or_create(
                        employee=emp,
                        date=d,
                        defaults={'status': att_status, 'source': 'holiday_calendar'},
                    )


class LeaveService:

    @staticmethod
    @transaction.atomic
    def approve(leave_id, user, request=None):
        leave = LeaveRequest.objects.select_for_update().get(id=leave_id)
        if not can_approve_for(user, leave.employee):
            raise PermissionDenied("You cannot approve this leave request.")
        if leave.status != 'pending':
            raise ValidationError({'detail': f'Leave is already {leave.status}.'})

        leave.status = 'approved'
        leave.reviewed_by = user
        leave.reviewed_on = timezone.now()
        leave.save()

        balance, _ = LeaveBalance.objects.select_for_update().get_or_create(employee=leave.employee)
        field = balance.bucket_field(leave.leave_type)
        if field:
            setattr(balance, field, getattr(balance, field) + leave.total_days)
            balance.save()

        att_status = LEAVE_TYPE_TO_STATUS.get(leave.leave_type, 'lop')
        is_single_day = (leave.from_date == leave.to_date)
        is_half = (leave.total_days == Decimal('0.5') and is_single_day)

        d = leave.from_date
        while d <= leave.to_date:
            Attendance.objects.update_or_create(
                employee=leave.employee, date=d,
                defaults={
                    'status': att_status,
                    'source': 'leave_approval',
                    'is_half_day': is_half,
                },
            )
            d += timedelta(days=1)

        write_audit(actor=user, model_name='LeaveRequest', object_id=leave.id,
                    action='transition', old_state='pending', new_state='approved', request=request)
        notify(user=leave.employee, kind='leave_approved',
               title='Leave approved',
               body=f'Your {leave.leave_type} leave ({leave.from_date} – {leave.to_date}) was approved.',
               link='/hrms?tab=leave', actor=user)
        return leave

    @staticmethod
    @transaction.atomic
    def reject(leave_id, user, reason, request=None):
        leave = LeaveRequest.objects.select_for_update().get(id=leave_id)
        if not can_approve_for(user, leave.employee):
            raise PermissionDenied("You cannot reject this leave request.")
        if leave.status != 'pending':
            raise ValidationError({'detail': f'Leave is already {leave.status}.'})
        if not (reason and reason.strip()):
            raise ValidationError({'rejection_reason': 'A reason is required to reject.'})

        leave.status = 'rejected'
        leave.reviewed_by = user
        leave.reviewed_on = timezone.now()
        leave.rejection_reason = reason
        leave.save()

        write_audit(actor=user, model_name='LeaveRequest', object_id=leave.id,
                    action='transition', old_state='pending', new_state='rejected', request=request)
        notify(user=leave.employee, kind='leave_rejected',
               title='Leave rejected',
               body=f'Your {leave.leave_type} leave was rejected: {reason}',
               link='/hrms?tab=leave', actor=user)
        return leave

    @staticmethod
    @transaction.atomic
    def cancel(leave_id, user, request=None):
        leave = LeaveRequest.objects.select_for_update().get(id=leave_id)
        if leave.employee_id != user.id or leave.status != 'pending':
            raise PermissionDenied("Only your own pending requests can be cancelled.")
        leave.status = 'cancelled'
        leave.save()
        return leave


class PayrollService:

    @classmethod
    @transaction.atomic
    def run_salary(cls, month, year, user=None, request=None):
        run = PayrollRun.objects.create(run_type='salary', month=month, year=year,
                                        triggered_by=user, status='running')
        count, errors = 0, []
        month_start = date(year, month, 1)
        month_end = date(year, month, calendar.monthrange(year, month)[1])

        paid_roles = ['Admin', 'Manager', 'Employee']
        from django.contrib.auth import get_user_model
        User = get_user_model()
        employees = list(
            User.objects.filter(is_active=True, user_type__in=paid_roles)
            .select_related('entity')
        )

        for emp in employees:
            try:
                # --- find effective compensation version ---
                comp = (
                    CompensationVersion.objects
                    .filter(
                        employee=emp,
                        effective_from__lte=month_start,
                    )
                    .filter(
                        models.Q(effective_to__isnull=True) | models.Q(effective_to__gte=month_end)
                    )
                    .order_by('-effective_from')
                    .first()
                )
                if not comp:
                    errors.append({
                        'employee': emp.id,
                        'employee_name': emp.full_name,
                        'error': 'No compensation version effective for this period.',
                    })
                    continue

                # --- gate: invariant — every working day must have an Attendance row ---
                _entity = emp.entity
                if _entity:
                    _off_weekdays = set(
                        WeeklyOffRule.objects.filter(entity=_entity).values_list('weekday', flat=True)
                    ) or {5, 6}
                    _holiday_dates = set(
                        WorkingCalendarEntry.objects.filter(
                            entity=_entity, entry_type='holiday',
                            date__year=year, date__month=month,
                        ).values_list('date', flat=True)
                    )
                else:
                    _off_weekdays = {5, 6}
                    _holiday_dates = set()

                _days_in_month = calendar.monthrange(year, month)[1]
                # Only require attendance up to yesterday — today's row may not be filed yet
                # (Celery runs on the 1st of next month, so month_end < today then; but for
                # manual mid-month runs we must not penalise employees for a day still in progress)
                _gate_end = min(date(year, month, _days_in_month), date.today() - timedelta(days=1))
                expected_working_dates = {
                    date(year, month, d)
                    for d in range(1, _days_in_month + 1)
                    if date(year, month, d).weekday() not in _off_weekdays
                    and date(year, month, d) not in _holiday_dates
                    and date(year, month, d) <= _gate_end
                }
                covered_dates = set(
                    Attendance.objects.filter(
                        employee=emp, date__year=year, date__month=month,
                    ).values_list('date', flat=True)
                )
                missing_days = len(expected_working_dates - covered_dates)
                unmarked_count = Attendance.objects.filter(
                    employee=emp, date__year=year, date__month=month, status='unmarked',
                ).count()

                gate_problems = []
                if missing_days:
                    gate_problems.append(f'{missing_days} working day(s) have no attendance record')
                if unmarked_count:
                    gate_problems.append(f'{unmarked_count} day(s) marked as unmarked')
                if gate_problems:
                    errors.append({
                        'employee': emp.id,
                        'employee_name': emp.full_name,
                        'error': 'Incomplete attendance for period — ' + '; '.join(gate_problems) + '. Resolve before running payroll.',
                    })
                    continue

                # --- attendance pass: LOP + breakdown snapshot ---
                att_rows = list(Attendance.objects.filter(
                    employee=emp, date__year=year, date__month=month,
                ))
                PAID_LEAVE_STATUSES = ('sick_leave', 'casual_leave', 'earned_leave')

                lop_days = Decimal('0')
                days_present = Decimal('0')
                paid_leave_days = Decimal('0')
                weekly_offs = 0
                public_holidays = 0

                for row in att_rows:
                    weight = Decimal('0.5') if row.is_half_day else Decimal('1')
                    if row.status in LOP_STATUSES:
                        lop_days += weight
                    elif row.status in ('present', 'wfh'):
                        days_present += weight
                    elif row.status == 'half_day':
                        days_present += Decimal('0.5')
                    elif row.status in PAID_LEAVE_STATUSES:
                        paid_leave_days += weight
                    elif row.status == 'weekly_off':
                        weekly_offs += 1
                    elif row.status == 'holiday':
                        public_holidays += 1

                # --- compensation components ---
                basic = comp.basic_salary or Decimal('0')
                hra = comp.hra or Decimal('0')
                special = comp.special_allowance or Decimal('0')
                conveyance = comp.conveyance_allowance or Decimal('0')
                medical = comp.medical_allowance or Decimal('0')
                other_allow = comp.other_allowance or Decimal('0')
                perf_bonus = comp.monthly_incentive or Decimal('0')
                gross = basic + hra + special + conveyance + medical + other_allow + perf_bonus

                entity = emp.entity
                working_days = _working_days_in_month(month, year, entity)

                if working_days and lop_days:
                    per_day_rate = (basic / Decimal(working_days)).quantize(
                        Decimal('0.01'), rounding=ROUND_HALF_UP
                    )
                    lop_deduction = (lop_days * per_day_rate).quantize(
                        Decimal('0.01'), rounding=ROUND_HALF_UP
                    )
                else:
                    lop_deduction = Decimal('0')

                # --- PT lookup ---
                pt = _get_professional_tax(entity, gross, month_start) if entity else Decimal('0')

                # --- TDS from compensation snapshot ---
                tds = comp.monthly_tds or Decimal('0')

                # --- advance recovery ---
                from .models import AdvanceSalaryRequest
                active_advances = list(
                    AdvanceSalaryRequest.objects.select_for_update().filter(
                        employee=emp, status='approved',
                    ).exclude(months_recovered__gte=models.F('proposed_recovery_months'))
                )
                advance_recovery = sum(
                    (a.monthly_recovery_amount for a in active_advances), Decimal('0')
                ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

                days_paid_for = Decimal(working_days) - lop_days

                total_deductions = (lop_deduction + pt + tds + advance_recovery).quantize(
                    Decimal('0.01'), rounding=ROUND_HALF_UP
                )
                net = (gross - total_deductions).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

                entity_name = entity.name if entity else ''

                PayrollRecord.objects.update_or_create(
                    employee=emp, month=month, year=year, slip_type='salary',
                    defaults=dict(
                        run=run,
                        entity=entity_name,
                        # earnings
                        basic_salary=basic,
                        hra=hra,
                        special_allowance=special,
                        conveyance_allowance=conveyance,
                        medical_allowance=medical,
                        performance_bonus=perf_bonus,
                        other_allowance=other_allow,
                        incentive_amount=Decimal('0'),
                        gross_earnings=gross,
                        # attendance
                        total_working_days=working_days,
                        days_present=days_present,
                        paid_leave_days=paid_leave_days,
                        weekly_offs=weekly_offs,
                        public_holidays=public_holidays,
                        days_paid_for=days_paid_for,
                        # deductions
                        lop_days=lop_days,
                        lop_deduction=lop_deduction,
                        professional_tax=pt,
                        tds_deduction=tds,
                        advance_recovery=advance_recovery,
                        other_deductions=Decimal('0'),
                        total_deductions=total_deductions,
                        net_amount=net,
                        status='sent',
                        sent_at=timezone.now(),
                    ),
                )

                # post-payroll: increment advance recovery counters
                for adv in active_advances:
                    adv.months_recovered += 1
                    if adv.months_recovered >= adv.proposed_recovery_months:
                        adv.status = 'recovered'
                    adv.save()
                count += 1
                notify(user=emp, kind='payslip_generated',
                       title='Your salary slip is ready',
                       body=f'Your salary slip for {month}/{year} has been generated. Net pay: ₹{net:,.2f}',
                       link='/hrms?tab=payroll', actor=user)
            except Exception as e:
                errors.append({'employee': emp.id, 'employee_name': emp.full_name, 'error': str(e)})

        run.records_generated = count
        run.errors = errors
        run.status = 'completed' if not errors else ('partial' if count else 'failed')
        run.completed_at = timezone.now()
        run.save()
        if user:
            write_audit(actor=user, model_name='PayrollRun', object_id=run.id,
                        action='run', new_state=run.status, request=request,
                        context={'count': count, 'errors': len(errors)})
        return run

    @classmethod
    @transaction.atomic
    def create_compensation_version(cls, employee, effective_from, basic_salary,
                                    hra=None, special_allowance=None, conveyance_allowance=None,
                                    medical_allowance=None, other_allowance=None,
                                    incentive=None, tds=None, actor=None, request=None):
        """Create new version, auto-close the previous current version the day before."""
        prev = (
            CompensationVersion.objects
            .filter(employee=employee, effective_to__isnull=True)
            .order_by('-effective_from')
            .first()
        )
        if prev:
            if prev.effective_from >= effective_from:
                raise ValidationError({
                    'effective_from': 'New version must be later than the current active version.'
                })
            prev.effective_to = effective_from - timedelta(days=1)
            prev.save()

        version = CompensationVersion.objects.create(
            employee=employee,
            effective_from=effective_from,
            effective_to=None,
            basic_salary=basic_salary,
            hra=hra or Decimal('0'),
            special_allowance=special_allowance or Decimal('0'),
            conveyance_allowance=conveyance_allowance or Decimal('0'),
            medical_allowance=medical_allowance or Decimal('0'),
            other_allowance=other_allowance or Decimal('0'),
            monthly_incentive=incentive or Decimal('0'),
            monthly_tds=tds or Decimal('0'),
        )
        if actor:
            write_audit(actor=actor, model_name='CompensationVersion', object_id=version.id,
                        action='created', new_state='active', request=request,
                        context={'effective_from': str(effective_from)})
        return version


class IncentiveService:

    @staticmethod
    @transaction.atomic
    def send(incentive_id, user=None, system=False, request=None):
        inc = Incentive.objects.select_for_update().get(id=incentive_id)
        if inc.status == 'sent':
            return inc
        entity_name = inc.employee.entity.name if inc.employee.entity_id else ''
        rec, _ = PayrollRecord.objects.update_or_create(
            employee=inc.employee, month=inc.month, year=inc.year, slip_type='incentive',
            defaults=dict(
                entity=entity_name,
                basic_salary=Decimal('0'),
                hra=Decimal('0'),
                special_allowance=Decimal('0'),
                conveyance_allowance=Decimal('0'),
                medical_allowance=Decimal('0'),
                performance_bonus=Decimal('0'),
                other_allowance=Decimal('0'),
                incentive_amount=inc.amount,
                gross_earnings=inc.amount,
                lop_days=Decimal('0'),
                lop_deduction=Decimal('0'),
                professional_tax=Decimal('0'),
                tds_deduction=Decimal('0'),
                advance_recovery=Decimal('0'),
                other_deductions=Decimal('0'),
                total_deductions=Decimal('0'),
                net_amount=inc.amount,
                status='sent',
                sent_at=timezone.now(),
            ),
        )
        inc.status = 'sent'
        inc.sent_at = timezone.now()
        inc.payroll_record = rec
        inc.save()
        write_audit(actor=user, actor_system='Celery' if system else None,
                    model_name='Incentive', object_id=inc.id, action='sent',
                    new_state='sent', request=request)
        notify(user=inc.employee, kind='incentive_sent',
               title='Incentive credited',
               body=f'An incentive of {inc.amount} has been processed.',
               link='/hrms?tab=payroll', actor=user)
        return inc
