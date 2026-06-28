from django.db import migrations, models
import documents.models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0002_shareddocument_url'),
    ]

    operations = [
        migrations.AddField(
            model_name='documentrequest',
            name='attachment_file',
            field=models.FileField(blank=True, null=True, upload_to=documents.models.request_attachment_path),
        ),
        migrations.AddField(
            model_name='documentrequest',
            name='attachment_url',
            field=models.URLField(blank=True, max_length=2048, null=True),
        ),
        migrations.AddField(
            model_name='documentrequest',
            name='attachment_filename',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
    ]
