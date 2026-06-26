from django.db import models
from django.conf import settings
from datetime import datetime


class LeaveBalance(models.Model):
    employee = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='leave_balance')
    sick_total = models.IntegerField(default=12)
    sick_used = models.IntegerField(default=0)
    casual_total = models.IntegerField(default=12)
    casual_used = models.IntegerField(default=0)
    earned_total = models.IntegerField(default=15)
    earned_used = models.IntegerField(default=0)
    unpaid_used = models.IntegerField(default=0)

    @property
    def sick_remaining(self):
        return self.sick_total - self.sick_used

    @property
    def casual_remaining(self):
        return self.casual_total - self.casual_used

    @property
    def earned_remaining(self):
        return self.earned_total - self.earned_used

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
    total_days = models.IntegerField()
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


class Compensation(models.Model):
    employee = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='compensation')
    monthly_base_salary = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.employee}'s Compensation"


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
    entity = models.CharField(max_length=50, blank=True)
    month = models.IntegerField()
    year = models.IntegerField()
    slip_type = models.CharField(max_length=20, choices=SLIP_TYPES)
    base_salary = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    incentive_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    advance_deduction = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    other_deductions = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    net_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='generated')
    generated_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-year', '-month']
        # Idempotency: one slip per employee/month/year/type
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
        # One incentive per employee per month (mergeable by editing).
        unique_together = ('employee', 'month', 'year')

    def __str__(self):
        return f"{self.employee} - {self.amount} ({self.status})"


class AdvanceSalaryRequest(models.Model):
    STATUS_CHOICES = [('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')]

    employee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='advance_requests')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.TextField()
    proposed_recovery_months = models.IntegerField()
    monthly_recovery_amount = models.DecimalField(max_digits=10, decimal_places=2)
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
        ('present', 'Present'), ('leave', 'Leave'), ('absent', 'Absent'),
        ('half_day', 'Half Day'), ('holiday', 'Holiday'),
    ]
    employee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                 related_name='attendances', db_index=True)
    date = models.DateField(db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='absent')
    marked_by_admin = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ('employee', 'date')
        ordering = ['-date']

    @property
    def working_hours(self):
        """Sum of all completed and active sessions (active calculated up to now)."""
        sessions = self.sessions.all()
        total_seconds = 0
        from datetime import datetime
        now = datetime.now().time()

        for session in sessions:
            base = datetime.combine(self.date, session.clock_in_time)
            # If active, use current time (if today) or 23:59:59 (if past day)
            if session.clock_out_time:
                out = datetime.combine(self.date, session.clock_out_time)
            else:
                from django.utils import timezone
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
