from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hrms', '0001_initial'),
    ]

    operations = [
        # --- CompensationVersion: rename + add allowance fields ---
        migrations.RenameField(
            model_name='compensationversion',
            old_name='monthly_base_salary',
            new_name='basic_salary',
        ),
        migrations.AlterField(
            model_name='compensationversion',
            name='basic_salary',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AlterField(
            model_name='compensationversion',
            name='monthly_incentive',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AlterField(
            model_name='compensationversion',
            name='monthly_tds',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name='compensationversion',
            name='hra',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name='compensationversion',
            name='special_allowance',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name='compensationversion',
            name='conveyance_allowance',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name='compensationversion',
            name='medical_allowance',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name='compensationversion',
            name='other_allowance',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),

        # --- PayrollRecord: rename base_salary, expand earnings + attendance + deductions ---
        migrations.RenameField(
            model_name='payrollrecord',
            old_name='base_salary',
            new_name='basic_salary',
        ),
        migrations.AlterField(
            model_name='payrollrecord',
            name='basic_salary',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AlterField(
            model_name='payrollrecord',
            name='incentive_amount',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AlterField(
            model_name='payrollrecord',
            name='gross_earnings',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AlterField(
            model_name='payrollrecord',
            name='lop_deduction',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AlterField(
            model_name='payrollrecord',
            name='professional_tax',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AlterField(
            model_name='payrollrecord',
            name='tds_deduction',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AlterField(
            model_name='payrollrecord',
            name='other_deductions',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AlterField(
            model_name='payrollrecord',
            name='total_deductions',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AlterField(
            model_name='payrollrecord',
            name='net_amount',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        # New earnings snapshot fields
        migrations.AddField(
            model_name='payrollrecord',
            name='hra',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name='payrollrecord',
            name='special_allowance',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name='payrollrecord',
            name='conveyance_allowance',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name='payrollrecord',
            name='medical_allowance',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name='payrollrecord',
            name='performance_bonus',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name='payrollrecord',
            name='other_allowance',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        # Attendance snapshot fields
        migrations.AddField(
            model_name='payrollrecord',
            name='total_working_days',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='payrollrecord',
            name='days_present',
            field=models.DecimalField(decimal_places=1, default=0, max_digits=4),
        ),
        migrations.AddField(
            model_name='payrollrecord',
            name='paid_leave_days',
            field=models.DecimalField(decimal_places=1, default=0, max_digits=4),
        ),
        migrations.AddField(
            model_name='payrollrecord',
            name='weekly_offs',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='payrollrecord',
            name='public_holidays',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='payrollrecord',
            name='days_paid_for',
            field=models.DecimalField(decimal_places=1, default=0, max_digits=5),
        ),
        # New deduction field
        migrations.AddField(
            model_name='payrollrecord',
            name='advance_recovery',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
    ]
