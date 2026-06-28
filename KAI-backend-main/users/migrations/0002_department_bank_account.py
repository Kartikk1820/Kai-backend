import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Department',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('entity', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='departments', to='users.entity',
                )),
            ],
            options={'ordering': ['name']},
        ),
        migrations.AddField(
            model_name='user',
            name='department',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='employees', to='users.department',
            ),
        ),
        migrations.AddField(
            model_name='user',
            name='pan_number',
            field=models.CharField(blank=True, max_length=10, null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='uan_number',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='is_pf_applicable',
            field=models.BooleanField(default=False),
        ),
        migrations.CreateModel(
            name='EmployeeBankAccount',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('bank_name', models.CharField(max_length=100)),
                ('account_number', models.CharField(max_length=30)),
                ('ifsc_code', models.CharField(blank=True, max_length=15)),
                ('is_active', models.BooleanField(default=True)),
                ('effective_from', models.DateField(auto_now_add=True)),
                ('employee', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='bank_accounts',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={'ordering': ['-effective_from']},
        ),
    ]
