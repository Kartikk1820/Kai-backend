from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bids', '0005_portal_credential_state_size'),
    ]

    operations = [
        migrations.AddField(model_name='client', name='owner_name', field=models.CharField(blank=True, max_length=255)),
        migrations.AddField(model_name='client', name='incorporation_date', field=models.DateField(blank=True, null=True)),
        migrations.AddField(model_name='client', name='state_of_incorporation', field=models.CharField(blank=True, max_length=150)),
        migrations.AddField(model_name='client', name='corporation_type', field=models.CharField(blank=True, max_length=100)),
        migrations.AddField(model_name='client', name='fein', field=models.CharField(blank=True, max_length=50)),
        migrations.AddField(model_name='client', name='duns', field=models.CharField(blank=True, max_length=50)),
        migrations.AddField(model_name='client', name='cage_code', field=models.CharField(blank=True, max_length=20)),
        migrations.AddField(model_name='client', name='everify_no', field=models.CharField(blank=True, max_length=50)),
        migrations.AddField(model_name='client', name='website', field=models.CharField(blank=True, max_length=255)),
        migrations.AddField(model_name='client', name='address', field=models.TextField(blank=True)),
        migrations.AddField(model_name='client', name='phone', field=models.CharField(blank=True, max_length=50)),
        migrations.AddField(model_name='client', name='email', field=models.CharField(blank=True, max_length=255)),
        migrations.AddField(model_name='client', name='fax', field=models.CharField(blank=True, max_length=50)),
        migrations.AddField(model_name='client', name='notes', field=models.TextField(blank=True)),
    ]
