import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0008_rename_task_types'),
    ]

    operations = [
        migrations.AddField(
            model_name='task',
            name='recurrence_type',
            field=models.CharField(
                choices=[('none', 'None'), ('daily', 'Daily'), ('weekly', 'Weekly'), ('monthly', 'Monthly'), ('yearly', 'Yearly')],
                default='none', max_length=10, db_index=True,
            ),
        ),
        migrations.AddField(
            model_name='task',
            name='recurrence_days',
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='task',
            name='recurrence_end_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='task',
            name='is_recurrence_template',
            field=models.BooleanField(default=False, db_index=True),
        ),
        migrations.AddField(
            model_name='task',
            name='recurrence_parent',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name='spawned_instances', to='tasks.task',
            ),
        ),
    ]
