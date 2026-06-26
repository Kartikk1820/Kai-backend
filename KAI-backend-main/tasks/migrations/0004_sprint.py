import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0003_alter_comment_options'),
    ]

    operations = [
        migrations.CreateModel(
            name='Sprint',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('goal', models.TextField(blank=True)),
                ('status', models.CharField(
                    choices=[('planning', 'Planning'), ('active', 'Active'), ('completed', 'Completed')],
                    db_index=True, default='planning', max_length=20,
                )),
                ('start_date', models.DateField(blank=True, null=True)),
                ('end_date', models.DateField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('team', models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name='sprints', to='tasks.team',
                )),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.AddField(
            model_name='task',
            name='task_type',
            field=models.CharField(
                choices=[('story', 'Story'), ('task', 'Task'), ('bug', 'Bug'), ('epic', 'Epic')],
                default='task', max_length=10,
            ),
        ),
        migrations.AddField(
            model_name='task',
            name='story_points',
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='task',
            name='sprint',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name='tasks', to='tasks.sprint',
            ),
        ),
    ]
