import django.db.models.deletion
from django.db import migrations, models


def migrate_sub_position_to_designation(apps, schema_editor):
    User = apps.get_model('users', 'User')
    Position = apps.get_model('users', 'Position')

    print()  # newline before per-user logging
    created_positions = {}

    for user in User.objects.exclude(sub_position__isnull=True).exclude(sub_position=''):
        raw = user.sub_position.strip()
        if not raw:
            continue

        # Case-insensitive match against existing Position names
        pos = Position.objects.filter(name__iexact=raw).first()
        if pos is None:
            if raw.lower() in created_positions:
                pos = created_positions[raw.lower()]
            else:
                pos = Position.objects.create(name=raw, description='', role_ids=[])
                created_positions[raw.lower()] = pos
                print(f'  [designation migration] Auto-created Position: "{raw}"')

        user.designation = pos
        user.save(update_fields=['designation'])


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0004_rename_role_user_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='designation',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='users', to='users.position',
            ),
        ),
        migrations.RunPython(
            migrate_sub_position_to_designation,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.RemoveField(
            model_name='user',
            name='sub_position',
        ),
    ]
