from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_rename_is_active_column'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='sub_position',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.CreateModel(
            name='Position',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('description', models.CharField(blank=True, default='', max_length=255)),
                ('role_ids', models.JSONField(blank=True, default=list)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
    ]
