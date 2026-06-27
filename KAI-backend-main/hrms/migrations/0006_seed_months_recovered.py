from django.db import migrations


def seed_months_recovered(apps, schema_editor):
    AdvanceSalaryRequest = apps.get_model('hrms', 'AdvanceSalaryRequest')
    PayrollRecord = apps.get_model('hrms', 'PayrollRecord')

    for adv in AdvanceSalaryRequest.objects.filter(status='approved'):
        # Count distinct salary slips with advance deductions generated after the advance was applied
        months_paid = PayrollRecord.objects.filter(
            employee=adv.employee,
            slip_type='salary',
            advance_deduction__gt=0,
        ).count()
        adv.months_recovered = min(months_paid, adv.proposed_recovery_months)
        if adv.months_recovered >= adv.proposed_recovery_months:
            adv.status = 'recovered'
        adv.save(update_fields=['months_recovered', 'status'])


class Migration(migrations.Migration):

    dependencies = [
        ('hrms', '0005_advancesalaryrequest_months_recovered_and_more'),
    ]

    operations = [
        migrations.RunPython(seed_months_recovered, migrations.RunPython.noop),
    ]
