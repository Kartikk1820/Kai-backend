import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('users', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='LeaveBalance',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sick_total', models.IntegerField(default=12)),
                ('sick_used', models.DecimalField(decimal_places=1, default=0, max_digits=5)),
                ('casual_total', models.IntegerField(default=12)),
                ('casual_used', models.DecimalField(decimal_places=1, default=0, max_digits=5)),
                ('earned_total', models.IntegerField(default=15)),
                ('earned_used', models.DecimalField(decimal_places=1, default=0, max_digits=5)),
                ('unpaid_used', models.DecimalField(decimal_places=1, default=0, max_digits=5)),
                ('employee', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='leave_balance',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
        ),
        migrations.CreateModel(
            name='LeaveRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('leave_type', models.CharField(
                    choices=[('sick', 'Sick'), ('casual', 'Casual'), ('earned', 'Earned'), ('unpaid', 'Unpaid')],
                    max_length=20,
                )),
                ('from_date', models.DateField()),
                ('to_date', models.DateField()),
                ('total_days', models.DecimalField(decimal_places=1, max_digits=4)),
                ('reason', models.TextField(blank=True, default='')),
                ('status', models.CharField(
                    choices=[('pending', 'Pending'), ('approved', 'Approved'),
                             ('rejected', 'Rejected'), ('cancelled', 'Cancelled')],
                    db_index=True, default='pending', max_length=20,
                )),
                ('applied_on', models.DateTimeField(auto_now_add=True)),
                ('reviewed_on', models.DateTimeField(blank=True, null=True)),
                ('rejection_reason', models.TextField(blank=True, null=True)),
                ('employee', models.ForeignKey(
                    db_index=True, on_delete=django.db.models.deletion.CASCADE,
                    related_name='leave_requests', to=settings.AUTH_USER_MODEL,
                )),
                ('reviewed_by', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='reviewed_leaves', to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={'ordering': ['-applied_on']},
        ),
        migrations.CreateModel(
            name='CompensationVersion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('effective_from', models.DateField()),
                ('effective_to', models.DateField(blank=True, null=True)),
                ('monthly_base_salary', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('monthly_incentive', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('monthly_tds', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('employee', models.ForeignKey(
                    db_index=True, on_delete=django.db.models.deletion.CASCADE,
                    related_name='compensation_versions', to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={'ordering': ['-effective_from']},
        ),
        migrations.AlterUniqueTogether(
            name='compensationversion',
            unique_together={('employee', 'effective_from')},
        ),
        migrations.CreateModel(
            name='PayrollRun',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('run_type', models.CharField(
                    choices=[('salary', 'Salary'), ('incentive', 'Incentive')], max_length=20,
                )),
                ('month', models.IntegerField()),
                ('year', models.IntegerField()),
                ('status', models.CharField(
                    choices=[('running', 'Running'), ('completed', 'Completed'),
                             ('partial', 'Partial'), ('failed', 'Failed')],
                    default='running', max_length=20,
                )),
                ('records_generated', models.IntegerField(default=0)),
                ('errors', models.JSONField(blank=True, default=list)),
                ('started_at', models.DateTimeField(auto_now_add=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('triggered_by', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='payroll_runs', to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={'ordering': ['-started_at']},
        ),
        migrations.CreateModel(
            name='PayrollRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('entity', models.CharField(blank=True, max_length=100)),
                ('month', models.IntegerField()),
                ('year', models.IntegerField()),
                ('slip_type', models.CharField(
                    choices=[('salary', 'Salary'), ('incentive', 'Incentive')], max_length=20,
                )),
                ('base_salary', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('incentive_amount', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('gross_earnings', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('lop_days', models.DecimalField(decimal_places=1, default=0, max_digits=5)),
                ('lop_deduction', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('professional_tax', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('tds_deduction', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('other_deductions', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('total_deductions', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('net_amount', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('status', models.CharField(
                    choices=[('generated', 'Generated'), ('sent', 'Sent')],
                    default='generated', max_length=20,
                )),
                ('generated_at', models.DateTimeField(auto_now_add=True)),
                ('sent_at', models.DateTimeField(blank=True, null=True)),
                ('notes', models.TextField(blank=True)),
                ('employee', models.ForeignKey(
                    db_index=True, on_delete=django.db.models.deletion.CASCADE,
                    related_name='payroll_records', to=settings.AUTH_USER_MODEL,
                )),
                ('run', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='records', to='hrms.payrollrun',
                )),
            ],
            options={'ordering': ['-year', '-month']},
        ),
        migrations.AlterUniqueTogether(
            name='payrollrecord',
            unique_together={('employee', 'month', 'year', 'slip_type')},
        ),
        migrations.CreateModel(
            name='Incentive',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('reason', models.TextField()),
                ('month', models.IntegerField()),
                ('year', models.IntegerField()),
                ('status', models.CharField(
                    choices=[('scheduled', 'Scheduled'), ('sent', 'Sent'), ('cancelled', 'Cancelled')],
                    db_index=True, default='scheduled', max_length=20,
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('sent_at', models.DateTimeField(blank=True, null=True)),
                ('employee', models.ForeignKey(
                    db_index=True, on_delete=django.db.models.deletion.CASCADE,
                    related_name='incentives', to=settings.AUTH_USER_MODEL,
                )),
                ('granted_by', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='granted_incentives', to=settings.AUTH_USER_MODEL,
                )),
                ('payroll_record', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='+', to='hrms.payrollrecord',
                )),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.AlterUniqueTogether(
            name='incentive',
            unique_together={('employee', 'month', 'year')},
        ),
        migrations.CreateModel(
            name='AdvanceSalaryRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('reason', models.TextField()),
                ('proposed_recovery_months', models.IntegerField()),
                ('monthly_recovery_amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('months_recovered', models.IntegerField(default=0)),
                ('status', models.CharField(
                    choices=[('pending', 'Pending'), ('approved', 'Approved'),
                             ('rejected', 'Rejected'), ('recovered', 'Recovered')],
                    default='pending', max_length=20,
                )),
                ('applied_on', models.DateTimeField(auto_now_add=True)),
                ('rejection_reason', models.TextField(blank=True, null=True)),
                ('employee', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='advance_requests', to=settings.AUTH_USER_MODEL,
                )),
                ('reviewed_by', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='reviewed_advances', to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={'ordering': ['-applied_on']},
        ),
        migrations.CreateModel(
            name='Attendance',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(db_index=True)),
                ('status', models.CharField(
                    choices=[
                        ('present', 'Present'), ('wfh', 'Work From Home'), ('half_day', 'Half Day'),
                        ('sick_leave', 'Sick Leave'), ('casual_leave', 'Casual Leave'),
                        ('earned_leave', 'Earned Leave'), ('lop', 'Loss of Pay'),
                        ('weekly_off', 'Weekly Off'), ('holiday', 'Holiday'),
                        ('unmarked', 'Unmarked'), ('absent', 'Absent'),
                    ],
                    default='unmarked', max_length=20,
                )),
                ('is_half_day', models.BooleanField(default=False)),
                ('source', models.CharField(
                    choices=[
                        ('clock_in', 'Clock In'), ('leave_approval', 'Leave Approval'),
                        ('admin_override', 'Admin Override'),
                        ('holiday_calendar', 'Holiday Calendar'), ('system', 'System'),
                    ],
                    default='system', max_length=20,
                )),
                ('notes', models.TextField(blank=True)),
                ('employee', models.ForeignKey(
                    db_index=True, on_delete=django.db.models.deletion.CASCADE,
                    related_name='attendances', to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={'ordering': ['-date']},
        ),
        migrations.AlterUniqueTogether(
            name='attendance',
            unique_together={('employee', 'date')},
        ),
        migrations.CreateModel(
            name='AttendanceSession',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('clock_in_time', models.TimeField()),
                ('clock_out_time', models.TimeField(blank=True, null=True)),
                ('attendance', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='sessions', to='hrms.attendance',
                )),
            ],
            options={'ordering': ['clock_in_time']},
        ),
        migrations.CreateModel(
            name='WeeklyOffRule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('weekday', models.IntegerField(choices=[
                    (0, 'Monday'), (1, 'Tuesday'), (2, 'Wednesday'), (3, 'Thursday'),
                    (4, 'Friday'), (5, 'Saturday'), (6, 'Sunday'),
                ])),
                ('entity', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='weekly_off_rules', to='users.entity',
                )),
            ],
            options={'ordering': ['entity', 'weekday']},
        ),
        migrations.AlterUniqueTogether(
            name='weeklyoffrule',
            unique_together={('entity', 'weekday')},
        ),
        migrations.CreateModel(
            name='WorkingCalendarEntry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('name', models.CharField(max_length=100)),
                ('entry_type', models.CharField(
                    choices=[('holiday', 'Holiday'), ('weekly_off', 'Weekly Off')],
                    default='holiday', max_length=20,
                )),
                ('entity', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='calendar_entries', to='users.entity',
                )),
            ],
            options={'ordering': ['date']},
        ),
        migrations.AlterUniqueTogether(
            name='workingcalendarentry',
            unique_together={('entity', 'date')},
        ),
        migrations.CreateModel(
            name='ProfessionalTaxSlab',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('effective_from', models.DateField()),
                ('income_from', models.DecimalField(decimal_places=2, max_digits=10)),
                ('income_to', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('monthly_tax', models.DecimalField(decimal_places=2, max_digits=8)),
                ('entity', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='pt_slabs', to='users.entity',
                )),
            ],
            options={'ordering': ['entity', 'effective_from', 'income_from']},
        ),
    ]
