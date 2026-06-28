from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0004_position_model'),
    ]

    operations = [
        migrations.RemoveField(model_name='user', name='pay_rate'),
        migrations.RemoveField(model_name='user', name='margin'),
        migrations.RemoveField(model_name='user', name='contract_period'),
    ]
