import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bids', '0010_bidopportunity_award_date_bidopportunity_poc_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='bidopportunity',
            name='status',
            field=models.CharField(
                choices=[('draft', 'Draft'), ('in_review', 'In Review'), ('pip', 'PIP'), ('cancelled', 'Cancelled')],
                db_index=True, default='draft', max_length=15,
            ),
        ),
        migrations.AddField(
            model_name='bidopportunity',
            name='cancellation_reason',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='client',
            name='linked_user',
            field=models.OneToOneField(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='client_profile',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name='portalcredential',
            name='client',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='portal_credentials',
                to='bids.client',
            ),
        ),
        migrations.AddField(
            model_name='portalcredential',
            name='client_bid',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='portal_credentials',
                to='bids.clientbid',
            ),
        ),
    ]
