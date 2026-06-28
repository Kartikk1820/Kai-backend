from decimal import Decimal
from datetime import datetime
from django.db import models
from django.conf import settings


class LeaveBalance(models.Model):
    employee = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='leave_balance')
    sick_total = models.IntegerField(default=12)
    sick_used = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    casual_total = models.IntegerField(default=12)
    casual_used = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    earned_total = models.IntegerField(default=15)
    earned_used = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    unpaid_used = models.DecimalField(max_digits=5, decimal_places=1, default=0)

    @property
    def sick_remaining(self):
        return Decimal(self.sick_total) - self.sick_used

    @property
    def casual_remaining(self):
        return Decimal(self.casual_total) - self.casual_used

    @property
    def earned_remaining(self):
        return Decimal(self.earned_total) - self.earned_used

    def bucket_field(self, leave_type):
        return {'sick': 'sick_used', 'casual': 'casual_used',
                'earned': 'earned_used', 'unpaid': 'unpaid_used'}.get(leave_type)

    def __str__(self):
        return f"{self.employee}'s Leave Balance"


class LeaveRequest(models.Model):
    LEAVE_TYPES = [('sick', 'Sick'), ('casual', 'Casual'), ('earned', 'Earned'), ('unpaid', 'Unpaid')]
    STATUS_CHOICES = [('pending', 'Pending'), ('approved', 'Approved'),
                      ('rejected', 'Rejected'), ('cancelled', 'Cancelled')]

    employee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                 related_name='leave_requests', db_index=True)
    leave_type = models.CharField(max_length=20, choices=LEAVE_TYPES)
    from_date = models.DateField()
    to_date = models.DateField()
    total_days = models.DecimalField(max_digits=4, decimal_places=1)
    reason = models.TextField(blank=True, default='')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True)
    applied_on = models.DateTimeField(auto_now_add=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name='reviewed_leaves')
    reviewed_on = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ['-applied_on']

    def __str__(self):
        return f"{self.employee} - {self.leave_type} ({self.status})"


class CompensationVersion(models.Model):
    employee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                 related_name='compensation_versions', db_index=True)
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    basic_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    hra = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    special_allowance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    conveyance_allowance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    medical_allowance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    other_allowance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    monthly_incentive = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    monthly_tds = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-effective_from']
        unique_together = ('employee', 'effective_from')

    def __str__(self):
        return f"{self.employee} comp from {self.effective_from}"


class PayrollRun(models.Model):
    TYPE_CHOICES = [('salary', 'Salary'), ('incentive', 'Incentive')]
    STATUS_CHOICES = [('running', 'Running'), ('completed', 'Completed'),
                      ('partial', 'Partial'), ('failed', 'Failed')]

    run_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    month = models.IntegerField()
    year = models.IntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='running')
    records_generated = models.IntegerField(default=0)
    errors = models.JSONField(default=list, blank=True)
    triggered_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                     on_delete=models.SET_NULL, related_name='payroll_runs')
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-started_at']

    def __str__(self):
        return f"{self.run_type} {self.month}/{self.year} ({self.status})"


class PayrollRecord(models.Model):
    SLIP_TYPES = [('salary', 'Salary'), ('incentive', 'Incentive')]
    STATUS_CHOICES = [('generated', 'Generated'), ('sent', 'Sent')]

    employee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                 related_name='payroll_records', db_index=True)
    run = models.ForeignKey(PayrollRun, null=True, blank=True, on_delete=models.SET_NULL, related_name='records')
    entity = models.CharField(max_length=100, blank=True)  # snapshot — not a live FK
    month = models.IntegerField()
    year = models.IntegerField()
    slip_type = models.CharField(max_length=20, choices=SLIP_TYPES)

    # Earnings snapshot
    basic_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    hra = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    special_allowance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    conveyance_allowance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    medical_allowance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    performance_bonus = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    other_allowance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    incentive_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    gross_earnings = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Attendance snapshot
    total_working_days = models.IntegerField(default=0)
    days_present = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    paid_leave_days = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    weekly_offs = models.IntegerField(default=0)
    public_holidays = models.IntegerField(default=0)
    days_paid_for = models.DecimalField(max_digits=5, decimal_places=1, default=0)

    # Deductions snapshot
    lop_days = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    lop_deduction = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    professional_tax = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tds_deduction = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    advance_recovery = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    other_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    net_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='generated')
    generated_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-year', '-month']
        unique_together = ('employee', 'month', 'year', 'slip_type')

    def __str__(self):
        return f"{self.employee} - {self.month}/{self.year} ({self.slip_type})"


class Incentive(models.Model):
    STATUS_CHOICES = [('scheduled', 'Scheduled'), ('sent', 'Sent'), ('cancelled', 'Cancelled')]

    employee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                 related_name='incentives', db_index=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.TextField()
    month = models.IntegerField()
    year = models.IntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled', db_index=True)
    granted_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                   on_delete=models.SET_NULL, related_name='granted_incentives')
    payroll_record = models.ForeignKey(PayrollRecord, null=True, blank=True,
                                       on_delete=models.SET_NULL, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('employee', 'month', 'year')

    def __str__(self):
        return f"{self.employee} - {self.amount} ({self.status})"


class AdvanceSalaryRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'), ('approved', 'Approved'),
        ('rejected', 'Rejected'), ('recovered', 'Recovered'),
    ]

    employee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                 related_name='advance_requests')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.TextField()
    proposed_recovery_months = models.IntegerField()
    monthly_recovery_amount = models.DecimalField(max_digits=10, decimal_places=2)
    months_recovered = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    applied_on = models.DateTimeField(auto_now_add=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name='reviewed_advances')
    rejection_reason = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ['-applied_on']

    def __str__(self):
        return f"{self.employee} - {self.amount} ({self.status})"


class Attendance(models.Model):
    STATUS_CHOICES = [
        ('present', 'Present'),
        ('wfh', 'Work From Home'),
        ('half_day', 'Half Day'),
        ('sick_leave', 'Sick Leave'),
        ('casual_leave', 'Casual Leave'),
        ('earned_leave', 'Earned Leave'),
        ('lop', 'Loss of Pay'),
        ('weekly_off', 'Weekly Off'),
        ('holiday', 'Holiday'),
        ('unmarked', 'Unmarked'),
        ('absent', 'Absent'),
    ]
    SOURCE_CHOICES = [
        ('clock_in', 'Clock In'),
        ('leave_approval', 'Leave Approval'),
        ('admin_override', 'Admin Override'),
        ('holiday_calendar', 'Holiday Calendar'),
        ('system', 'System'),
    ]

    employee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                 related_name='attendances', db_index=True)
    date = models.DateField(db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='unmarked')
    # Only meaningful on leave-type statuses (sick_leave, casual_leave, earned_leave, lop).
    is_half_day = models.BooleanField(default=False)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='system')
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ('employee', 'date')
        ordering = ['-date']

    @property
    def marked_by_admin(self):
        return self.source == 'admin_override'

    @property
    def working_hours(self):
        sessions = self.sessions.all()
        total_seconds = 0
        from django.utils import timezone
        for session in sessions:
            base = datetime.combine(self.date, session.clock_in_time)
            if session.clock_out_time:
                out = datetime.combine(self.date, session.clock_out_time)
            else:
                if timezone.localtime().date() == self.date:
                    out = datetime.combine(self.date, timezone.localtime().time())
                else:
                    out = datetime.combine(self.date, datetime.strptime('23:59:59', '%H:%M:%S').time())
            if out < base:
                from datetime import timedelta
                out += timedelta(days=1)
            total_seconds += (out - base).total_seconds()
        return round(total_seconds / 3600, 2)

    def __str__(self):
        return f"{self.employee} - {self.date} ({self.status})"


class AttendanceSession(models.Model):
    attendance = models.ForeignKey(Attendance, on_delete=models.CASCADE, related_name='sessions')
    clock_in_time = models.TimeField()
    clock_out_time = models.TimeField(null=True, blank=True)

    class Meta:
        ordering = ['clock_in_time']

    def __str__(self):
        return f"Session for {self.attendance} ({self.clock_in_time} - {self.clock_out_time or 'Active'})"


class WeeklyOffRule(models.Model):
    WEEKDAY_CHOICES = [
        (0, 'Monday'), (1, 'Tuesday'), (2, 'Wednesday'),
        (3, 'Thursday'), (4, 'Friday'), (5, 'Saturday'), (6, 'Sunday'),
    ]
    entity = models.ForeignKey('users.Entity', on_delete=models.CASCADE, related_name='weekly_off_rules')
    weekday = models.IntegerField(choices=WEEKDAY_CHOICES)

    class Meta:
        ordering = ['entity', 'weekday']
        unique_together = ('entity', 'weekday')

    def __str__(self):
        return f"{self.entity} — {self.get_weekday_display()}"


class WorkingCalendarEntry(models.Model):
    ENTRY_TYPES = [('holiday', 'Holiday'), ('weekly_off', 'Weekly Off')]
    entity = models.ForeignKey('users.Entity', on_delete=models.CASCADE, related_name='calendar_entries')
    date = models.DateField()
    name = models.CharField(max_length=100)
    entry_type = models.CharField(max_length=20, choices=ENTRY_TYPES, default='holiday')

    class Meta:
        ordering = ['date']
        unique_together = ('entity', 'date')

    def __str__(self):
        return f"{self.entity} — {self.date} ({self.name})"


class ProfessionalTaxSlab(models.Model):
    entity = models.ForeignKey('users.Entity', on_delete=models.CASCADE, related_name='pt_slabs')
    effective_from = models.DateField()
    income_from = models.DecimalField(max_digits=10, decimal_places=2)
    income_to = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    monthly_tax = models.DecimalField(max_digits=8, decimal_places=2)

    class Meta:
        ordering = ['entity', 'effective_from', 'income_from']

    def __str__(self):
        ceiling = str(self.income_to) if self.income_to else '∞'
        return f"{self.entity} PT [{self.income_from}–{ceiling}] = {self.monthly_tax}"
