from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    Attendance, LeaveBalance, LeaveRequest, PayrollRecord, AdvanceSalaryRequest,
    CompensationVersion, Incentive, PayrollRun,
    WeeklyOffRule, WorkingCalendarEntry, ProfessionalTaxSlab,
)
from users.models import Entity, Department, EmployeeBankAccount, Position

User = get_user_model()


def _emp_name(obj):
    name = f"{obj.employee.first_name} {obj.employee.last_name}".strip()
    return name or obj.employee.email


class EntitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Entity
        fields = ['id', 'name', 'code', 'state', 'is_active']


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ['id', 'name', 'entity_id']


class EmployeeBankAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeBankAccount
        fields = ['id', 'bank_name', 'account_number', 'ifsc_code', 'is_active', 'effective_from']
        read_only_fields = ['id', 'effective_from']


class WeeklyOffRuleSerializer(serializers.ModelSerializer):
    weekday_display = serializers.CharField(source='get_weekday_display', read_only=True)

    class Meta:
        model = WeeklyOffRule
        fields = ['id', 'entity', 'weekday', 'weekday_display']


class WorkingCalendarEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkingCalendarEntry
        fields = ['id', 'entity', 'date', 'name', 'entry_type']


class ProfessionalTaxSlabSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProfessionalTaxSlab
        fields = ['id', 'entity', 'effective_from', 'income_from', 'income_to', 'monthly_tax']


class AttendanceSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    working_hours = serializers.FloatField(read_only=True)
    clock_in_time = serializers.SerializerMethodField()
    clock_out_time = serializers.SerializerMethodField()

    class Meta:
        model = Attendance
        fields = [
            'id', 'employee_id', 'employee_name', 'date', 'status', 'is_half_day',
            'source', 'clock_in_time', 'clock_out_time', 'working_hours', 'notes',
        ]
        read_only_fields = [
            'id', 'employee_id', 'employee_name', 'working_hours',
            'clock_in_time', 'clock_out_time',
        ]

    def get_clock_in_time(self, obj):
        first = obj.sessions.order_by('clock_in_time').first()
        return first.clock_in_time.strftime('%H:%M:%S') if first else None

    def get_clock_out_time(self, obj):
        last = obj.sessions.order_by('-clock_in_time').first()
        if last and last.clock_out_time:
            return last.clock_out_time.strftime('%H:%M:%S')
        return None

    def get_employee_name(self, obj):
        return _emp_name(obj)


class LeaveBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveBalance
        fields = [
            'employee_id',
            'sick_total', 'sick_used', 'sick_remaining',
            'casual_total', 'casual_used', 'casual_remaining',
            'earned_total', 'earned_used', 'earned_remaining',
            'unpaid_used',
        ]


class LeaveRequestSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    reason = serializers.CharField(allow_blank=True, required=False, default='')

    class Meta:
        model = LeaveRequest
        fields = [
            'id', 'employee_id', 'employee_name', 'leave_type', 'from_date', 'to_date',
            'total_days', 'reason', 'status', 'applied_on', 'reviewed_by',
            'reviewed_on', 'rejection_reason',
        ]
        read_only_fields = [
            'id', 'employee_id', 'employee_name', 'status', 'applied_on',
            'reviewed_by', 'reviewed_on', 'rejection_reason',
        ]

    def get_employee_name(self, obj):
        return _emp_name(obj)


class CompensationVersionSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    employee_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='employee'
    )

    class Meta:
        model = CompensationVersion
        fields = [
            'id', 'employee_id', 'employee_name',
            'effective_from', 'effective_to',
            'basic_salary', 'hra', 'special_allowance', 'conveyance_allowance',
            'medical_allowance', 'other_allowance', 'monthly_incentive', 'monthly_tds',
            'created_at',
        ]
        read_only_fields = ['id', 'employee_name', 'effective_to', 'created_at']

    def get_employee_name(self, obj):
        name = f"{obj.employee.first_name} {obj.employee.last_name}".strip()
        return name or obj.employee.email

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret['employee_id'] = instance.employee_id
        return ret


class PayrollRecordSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()

    class Meta:
        model = PayrollRecord
        fields = [
            'id', 'employee_id', 'employee_name', 'entity', 'month', 'year', 'slip_type',
            # earnings
            'basic_salary', 'hra', 'special_allowance', 'conveyance_allowance',
            'medical_allowance', 'performance_bonus', 'other_allowance',
            'incentive_amount', 'gross_earnings',
            # attendance
            'total_working_days', 'days_present', 'paid_leave_days',
            'weekly_offs', 'public_holidays', 'days_paid_for',
            # deductions
            'lop_days', 'lop_deduction', 'professional_tax', 'tds_deduction',
            'advance_recovery', 'other_deductions', 'total_deductions',
            'net_amount', 'status', 'generated_at', 'sent_at', 'notes',
        ]

    def get_employee_name(self, obj):
        return _emp_name(obj)


class PayrollRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayrollRun
        fields = ['id', 'run_type', 'month', 'year', 'status', 'records_generated',
                  'errors', 'started_at', 'completed_at']


class IncentiveSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    employee_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='employee'
    )

    class Meta:
        model = Incentive
        fields = ['id', 'employee_id', 'employee_name', 'amount', 'reason', 'month', 'year',
                  'status', 'created_at', 'sent_at']
        read_only_fields = ['id', 'employee_name', 'status', 'created_at', 'sent_at']

    def get_employee_name(self, obj):
        return _emp_name(obj)

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret['employee_id'] = instance.employee_id
        return ret


class AdvanceSalaryRequestSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()

    class Meta:
        model = AdvanceSalaryRequest
        fields = [
            'id', 'employee_id', 'employee_name', 'amount', 'reason',
            'proposed_recovery_months', 'monthly_recovery_amount', 'months_recovered',
            'status', 'applied_on', 'reviewed_by', 'rejection_reason',
        ]
        read_only_fields = [
            'id', 'employee_id', 'employee_name', 'monthly_recovery_amount',
            'months_recovered', 'status', 'applied_on', 'reviewed_by', 'rejection_reason',
        ]

    def get_employee_name(self, obj):
        return _emp_name(obj)


class EmployeeDetailSerializer(serializers.ModelSerializer):
    current_compensation = serializers.SerializerMethodField()
    leave_balance = LeaveBalanceSerializer(read_only=True)
    full_name = serializers.CharField(read_only=True)
    avatar_initials = serializers.CharField(read_only=True)
    entity_id = serializers.PrimaryKeyRelatedField(source='entity', read_only=True)
    entity = serializers.SerializerMethodField()
    department_id = serializers.PrimaryKeyRelatedField(source='department', read_only=True)
    department = serializers.SerializerMethodField()
    designation_id = serializers.PrimaryKeyRelatedField(source='designation', read_only=True)
    designation = serializers.SerializerMethodField()
    active_bank_account = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name', 'avatar_initials',
            'user_type', 'designation', 'designation_id', 'manager', 'is_active', 'date_joined',
            'phone_number', 'date_of_joining',
            'entity_id', 'entity',
            'department_id', 'department',
            'pan_number', 'uan_number', 'is_pf_applicable',
            'current_compensation', 'leave_balance', 'active_bank_account',
        ]

    def get_entity(self, obj):
        return obj.entity.name if obj.entity_id else None

    def get_department(self, obj):
        return obj.department.name if obj.department_id else None

    def get_designation(self, obj):
        return obj.designation.name if obj.designation_id else None

    def get_active_bank_account(self, obj):
        acct = obj.bank_accounts.filter(is_active=True).first()
        return EmployeeBankAccountSerializer(acct).data if acct else None

    def get_current_compensation(self, obj):
        from django.db.models import Q
        comp = (
            obj.compensation_versions
            .filter(Q(effective_to__isnull=True))
            .order_by('-effective_from')
            .first()
        )
        if comp is None:
            return None
        return CompensationVersionSerializer(comp).data


class EmployeeUpdateSerializer(serializers.ModelSerializer):
    date_of_joining = serializers.DateField(required=False, allow_null=True)
    entity_id = serializers.PrimaryKeyRelatedField(
        queryset=Entity.objects.all(), source='entity', allow_null=True, required=False,
    )
    department_id = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(), source='department', allow_null=True, required=False,
    )
    designation_id = serializers.PrimaryKeyRelatedField(
        queryset=Position.objects.all(), source='designation', allow_null=True, required=False,
    )

    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'user_type', 'designation_id', 'entity_id', 'department_id',
            'phone_number', 'date_of_joining', 'is_active',
            'pan_number', 'uan_number', 'is_pf_applicable',
        ]
        extra_kwargs = {
            'first_name': {'required': False},
            'last_name': {'required': False},
            'user_type': {'required': False},
            'phone_number': {'required': False, 'allow_blank': True},
            'is_active': {'required': False},
            'pan_number': {'required': False, 'allow_null': True, 'allow_blank': True},
            'uan_number': {'required': False, 'allow_null': True, 'allow_blank': True},
            'is_pf_applicable': {'required': False},
        }
