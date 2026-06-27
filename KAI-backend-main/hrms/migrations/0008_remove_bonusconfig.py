from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('hrms', '0007_compensation_monthly_incentive'),
    ]

    operations = [
        migrations.DeleteModel(name='BonusConfig'),
    ]
