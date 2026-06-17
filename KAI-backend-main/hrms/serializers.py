from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    Attendance, LeaveBalance, LeaveRequest, PayrollRecord, AdvanceSalaryRequest,
    Compensation, Incentive, PayrollRun,
)

User = get_user_model()


def _emp_name(obj):
    name = f"{obj.employee.first_name} {obj.employee.last_name}".strip()
    return name or obj.employee.email


class AttendanceSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    working_hours = serializers.FloatField(read_only=True)
    clock_in_time = serializers.SerializerMethodField()
    clock_out_time = serializers.SerializerMethodField()

    class Meta:
        model = Attendance
        fields = ['id', 'employee_id', 'employee_name', 'date', 'status',
                  'clock_in_time', 'clock_out_time', 'working_hours',
                  'marked_by_admin', 'notes']
        read_only_fields = ['id', 'employee_id', 'employee_name', 'working_hours', 'clock_in_time', 'clock_out_time']

    def get_clock_in_time(self, obj):
        first_session = obj.sessions.order_by('clock_in_time').first()
        return first_session.clock_in_time.strftime('%H:%M:%S') if first_session else None

    def get_clock_out_time(self, obj):
        last_session = obj.sessions.order_by('-clock_in_time').first()
        if last_session and last_session.clock_out_time:
            return last_session.clock_out_time.strftime('%H:%M:%S')
        return None

    def get_employee_name(self, obj):
        return _emp_name(obj)


class LeaveBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveBalance
        fields = ['employee_id', 'sick_total', 'sick_used', 'sick_remaining',
                  'casual_total', 'casual_used', 'casual_remaining',
                  'earned_total', 'earned_used', 'earned_remaining', 'unpaid_used']


class LeaveRequestSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()

    class Meta:
        model = LeaveRequest
        fields = ['id', 'employee_id', 'employee_name', 'leave_type', 'from_date', 'to_date',
                  'total_days', 'reason', 'status', 'applied_on', 'reviewed_by',
                  'reviewed_on', 'rejection_reason']
        read_only_fields = ['id', 'employee_id', 'employee_name', 'status', 'applied_on',
                            'reviewed_by', 'reviewed_on', 'rejection_reason']

    def get_employee_name(self, obj):
        return _emp_name(obj)


class PayrollRecordSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()

    class Meta:
        model = PayrollRecord
        fields = ['id', 'employee_id', 'employee_name', 'entity', 'month', 'year', 'slip_type',
                  'base_salary', 'incentive_amount', 'advance_deduction', 'other_deductions',
                  'net_amount', 'status', 'generated_at', 'sent_at', 'notes']

    def get_employee_name(self, obj):
        return _emp_name(obj)


class PayrollRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayrollRun
        fields = ['id', 'run_type', 'month', 'year', 'status', 'records_generated',
                  'errors', 'started_at', 'completed_at']


class IncentiveSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()

    class Meta:
        model = Incentive
        fields = ['id', 'employee_id', 'employee_name', 'amount', 'reason', 'month', 'year',
                  'status', 'created_at', 'sent_at']
        read_only_fields = ['id', 'employee_name', 'status', 'created_at', 'sent_at']

    def get_employee_name(self, obj):
        return _emp_name(obj)


class AdvanceSalaryRequestSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()

    class Meta:
        model = AdvanceSalaryRequest
        fields = ['id', 'employee_id', 'employee_name', 'amount', 'reason',
                  'proposed_recovery_months', 'monthly_recovery_amount', 'status',
                  'applied_on', 'reviewed_by', 'rejection_reason']
        read_only_fields = ['id', 'employee_id', 'employee_name', 'status', 'applied_on',
                            'reviewed_by', 'rejection_reason']

    def get_employee_name(self, obj):
        return _emp_name(obj)


class CompensationSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    employee_id = serializers.IntegerField()

    class Meta:
        model = Compensation
        fields = ['id', 'employee_id', 'employee_name', 'monthly_base_salary']

    def get_employee_name(self, obj):
        return _emp_name(obj)


class EmployeeDetailSerializer(serializers.ModelSerializer):
    compensation = CompensationSerializer(read_only=True)
    leave_balance = LeaveBalanceSerializer(read_only=True)
    full_name = serializers.CharField(read_only=True)
    avatar_initials = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'full_name', 'avatar_initials',
                  'role', 'sub_position', 'manager', 'is_active', 'date_joined',
                  'phone_number', 'date_of_joining', 'entity', 'compensation', 'leave_balance']
