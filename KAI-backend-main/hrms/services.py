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
    PayrollRun, Incentive,
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

    @classmethod
    @transaction.atomic
    def run_salary(cls, month, year, user=None, request=None):
        run = PayrollRun.objects.create(run_type='salary', month=month, year=year,
                                        triggered_by=user, status='running')
        count, errors = 0, []
        paid_roles = ['Admin', 'Manager', 'Employee']
        comps = Compensation.objects.select_related('employee').filter(
            employee__is_active=True,
            employee__role__in=paid_roles,
        )
        for comp in comps:
            emp = comp.employee
            base = comp.monthly_base_salary or Decimal('0')
            incentive = comp.monthly_incentive or Decimal('0')
            net = base + incentive
            try:
                PayrollRecord.objects.update_or_create(
                    employee=emp, month=month, year=year, slip_type='salary',
                    defaults=dict(
                        run=run, entity=emp.entity or '', base_salary=base,
                        incentive_amount=incentive, net_amount=net,
                        status='sent', sent_at=timezone.now(),
                    ),
                )
                count += 1
                notify(user=emp, kind='payslip_generated',
                       title='Your salary slip is ready',
                       body=f'Your salary slip for {month}/{year} has been generated. Net pay: ₹{net:,.2f}',
                       link='/hrms?tab=payroll', actor=user)
            except Exception as e:
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
