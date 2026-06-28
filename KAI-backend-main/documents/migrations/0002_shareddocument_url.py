from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='shareddocument',
            name='url',
            field=models.URLField(blank=True, max_length=2048, null=True),
        ),
        migrations.AddField(
            model_name='shareddocument',
            name='link_label',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AlterField(
            model_name='shareddocument',
            name='file',
            field=models.FileField(blank=True, null=True, upload_to='documents/shared/'),
        ),
    ]
