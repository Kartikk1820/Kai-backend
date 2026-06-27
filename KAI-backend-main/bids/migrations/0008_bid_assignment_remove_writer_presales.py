from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def migrate_writer_presales_to_assignments(apps, schema_editor):
    ClientBid = apps.get_model('bids', 'ClientBid')
    BidAssignment = apps.get_model('bids', 'BidAssignment')

    for bid in ClientBid.objects.all():
        if bid.writer_id:
            BidAssignment.objects.get_or_create(
                client_bid=bid, user_id=bid.writer_id,
                defaults={'role': 'writer'}
            )
        if bid.presales_person_id and bid.presales_person_id != bid.writer_id:
            BidAssignment.objects.get_or_create(
                client_bid=bid, user_id=bid.presales_person_id,
                defaults={'role': 'presales'}
            )


class Migration(migrations.Migration):

    dependencies = [
        ('bids', '0007_clientbid_contract_value'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='BidAssignment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(choices=[('writer', 'Writer'), ('presales', 'Pre-sales'), ('reviewer', 'Reviewer')], default='writer', max_length=30)),
                ('assigned_at', models.DateTimeField(auto_now_add=True)),
                ('client_bid', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='assignments', to='bids.clientbid')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bid_assignments', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['role', 'assigned_at'],
                'unique_together': {('client_bid', 'user')},
            },
        ),
        migrations.RunPython(migrate_writer_presales_to_assignments, migrations.RunPython.noop),
        migrations.RemoveField(model_name='clientbid', name='presales_person'),
        migrations.RemoveField(model_name='clientbid', name='writer'),
    ]
