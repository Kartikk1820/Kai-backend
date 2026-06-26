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
    PayrollRun, Incentive, AdvanceSalaryRequest, BonusConfig,
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
        # Only internal employees get salary; exclude Clients
        paid_roles = ['Admin', 'Manager', 'Employee']
        comps = Compensation.objects.select_related('employee').filter(
            employee__is_active=True,
            employee__role__in=paid_roles,
        )
        for comp in comps:
            emp = comp.employee
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
                        net_amount=net, status='sent', sent_at=timezone.now(),
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

    @classmethod
    @transaction.atomic
    def run_bid_bonuses(cls, month, year, user=None, system=False, request=None):
        """Calculate bid-based bonuses for submitted bids in month/year window."""
        from bids.models import ClientBid
        from collections import defaultdict
        from django.contrib.auth import get_user_model

        User = get_user_model()
        config = BonusConfig.get()

        # Submitted bids whose status was last updated in the target month/year
        submitted_bids = list(
            ClientBid.objects.filter(
                status='submitted',
                updated_at__year=year,
                updated_at__month=month,
            ).select_related('writer', 'presales_person')
        )

        paid_roles = {'Admin', 'Manager', 'Employee'}
        bonuses: dict = defaultdict(Decimal)
        bid_counts: dict = defaultdict(int)

        for bid in submitted_bids:
            if bid.contract_value and bid.contract_value > 0:
                w_amt = (bid.contract_value * config.writer_bonus_pct / 100).quantize(Decimal('0.01'))
                p_amt = (bid.contract_value * config.presales_bonus_pct / 100).quantize(Decimal('0.01'))
            else:
                w_amt = config.flat_bonus_per_bid
                p_amt = config.flat_bonus_per_bid

            if bid.writer_id and bid.writer and bid.writer.role in paid_roles:
                bonuses[bid.writer_id] += w_amt
                bid_counts[bid.writer_id] += 1

            if (bid.presales_person_id and bid.presales_person
                    and bid.presales_person.role in paid_roles
                    and bid.presales_person_id != bid.writer_id):
                bonuses[bid.presales_person_id] += p_amt
                bid_counts[bid.presales_person_id] += 1

        count = 0
        for emp_id, amount in bonuses.items():
            if amount <= 0:
                continue
            try:
                emp = User.objects.get(id=emp_id)
            except User.DoesNotExist:
                continue
            reason = f'Bid bonus for {month}/{year} — {bid_counts[emp_id]} submitted bid(s)'
            inc, created = Incentive.objects.get_or_create(
                employee_id=emp_id, month=month, year=year,
                defaults=dict(amount=amount, reason=reason, granted_by=user, status='scheduled'),
            )
            if not created and inc.status == 'scheduled':
                inc.amount = amount
                inc.reason = reason
                inc.granted_by = user
                inc.save()
            count += 1
            notify(user=emp, kind='incentive_granted',
                   title='Bid bonus scheduled',
                   body=f'A bid bonus of ₹{amount:,.2f} is scheduled for {month}/{year}.',
                   link='/hrms?tab=payroll', actor=user)

        actor_system = 'Celery' if system else None
        write_audit(actor=user, actor_system=actor_system, model_name='BonusRun', object_id=0,
                    action='bid_bonus_run', new_state='completed', request=request,
                    context={'month': month, 'year': year, 'count': count,
                             'bids_processed': len(submitted_bids)})
        return {'count': count, 'bids_processed': len(submitted_bids)}


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
