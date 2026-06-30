from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_alter_user_groups'),
    ]

    operations = [
        migrations.RenameField(
            model_name='user',
            old_name='role',
            new_name='user_type',
        ),
    ]
