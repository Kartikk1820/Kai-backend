from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('hrms', '0008_remove_bonusconfig'),
    ]

    operations = [
        migrations.RemoveField(model_name='payrollrecord', name='advance_deduction'),
        migrations.RemoveField(model_name='payrollrecord', name='other_deductions'),
    ]
