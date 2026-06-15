"""HRMS service layer: leave approval (atomic), payroll & incentive generation."""
from datetime import timedelta, date
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from core.services import write_audit
from core.permissions_catalog import HR_APPROVE_LEAVE
from notifications.services import notify
from .models import (
    LeaveRequest, LeaveBalance, Attendance, Compensation, PayrollRecord,
    PayrollRun, Incentive, AdvanceSalaryRequest,
)


def can_approve_for(user, employee):
    """Admin/HR (permission) OR the employee's direct manager."""
    if user.role == 'Admin' or user.has_perm_key(HR_APPROVE_LEAVE):
        return True
    return employee.manager_id == user.id


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

        # Decrement balance
        balance, _ = LeaveBalance.objects.select_for_update().get_or_create(employee=leave.employee)
        field = balance.bucket_field(leave.leave_type)
        if field:
            setattr(balance, field, getattr(balance, field) + leave.total_days)
            balance.save()

        # Write attendance rows across the date range as 'leave'
        d = leave.from_date
        while d <= leave.to_date:
            Attendance.objects.update_or_create(
                employee=leave.employee, date=d,
                defaults={'status': 'leave', 'marked_by_admin': True},
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

    @staticmethod
    def _advance_recovery(employee):
        total = Decimal('0')
        for adv in AdvanceSalaryRequest.objects.filter(employee=employee, status='approved'):
            total += adv.monthly_recovery_amount
        return total

    @staticmethod
    def _unpaid_deduction(employee, month, year, base_salary):
        unpaid_days = Attendance.objects.filter(
            employee=employee, date__month=month, date__year=year, status='leave'
        ).filter(
            employee__leave_requests__leave_type='unpaid',
            employee__leave_requests__status='approved',
        ).distinct().count()
        if unpaid_days:
            per_day = base_salary / Decimal('30')
            return (per_day * unpaid_days).quantize(Decimal('0.01'))
        return Decimal('0')

    @classmethod
    @transaction.atomic
    def run_salary(cls, month, year, user=None, request=None):
        run = PayrollRun.objects.create(run_type='salary', month=month, year=year,
                                        triggered_by=user, status='running')
        count, errors = 0, []
        for comp in Compensation.objects.select_related('employee').all():
            emp = comp.employee
            if not emp.is_active:
                continue
            base = comp.monthly_base_salary or Decimal('0')
            advance = cls._advance_recovery(emp)
            unpaid = cls._unpaid_deduction(emp, month, year, base)
            net = base - advance - unpaid
            try:
                rec, created = PayrollRecord.objects.update_or_create(
                    employee=emp, month=month, year=year, slip_type='salary',
                    defaults=dict(
                        run=run, entity=emp.entity or '', base_salary=base,
                        advance_deduction=advance, other_deductions=unpaid,
                        net_amount=net, status='generated',
                    ),
                )
                count += 1
            except Exception as e:  # pragma: no cover
                errors.append({'employee': emp.id, 'error': str(e)})

        run.records_generated = count
        run.errors = errors
        run.status = 'completed' if not errors else 'partial'
        run.completed_at = timezone.now()
        run.save()
        if user:
            write_audit(actor=user, actor_system=None, model_name='PayrollRun', object_id=run.id,
                        action='run', new_state=run.status, request=request,
                        context={'count': count})
        return run


class IncentiveService:

    @staticmethod
    @transaction.atomic
    def send(incentive_id, user=None, system=False, request=None):
        inc = Incentive.objects.select_for_update().get(id=incentive_id)
        if inc.status == 'sent':
            return inc
        rec, _ = PayrollRecord.objects.update_or_create(
            employee=inc.employee, month=inc.month, year=inc.year, slip_type='incentive',
            defaults=dict(entity=inc.employee.entity or '', base_salary=Decimal('0'),
                          incentive_amount=inc.amount, net_amount=inc.amount,
                          status='sent', sent_at=timezone.now()),
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
