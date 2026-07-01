import django.db.models.deletion
import documents.models
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0004_alter_shareddocument_file'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='DocumentSendApproval',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(
                    choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected'), ('escalated', 'Escalated')],
                    db_index=True, default='pending', max_length=20,
                )),
                ('file', models.FileField(blank=True, null=True, upload_to=documents.models.approval_document_path)),
                ('url', models.URLField(blank=True, max_length=2048, null=True)),
                ('link_label', models.CharField(blank=True, max_length=255)),
                ('filename', models.CharField(max_length=255)),
                ('size', models.PositiveIntegerField(default=0)),
                ('content_type', models.CharField(blank=True, max_length=120)),
                ('message', models.TextField(blank=True)),
                ('escalation_minutes', models.PositiveIntegerField(default=240)),
                ('rejection_comment', models.TextField(blank=True)),
                ('escalated_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('sender', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='outgoing_approvals', to=settings.AUTH_USER_MODEL,
                )),
                ('recipient', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='incoming_doc_approvals', to=settings.AUTH_USER_MODEL,
                )),
                ('approver', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='approval_tasks', to=settings.AUTH_USER_MODEL,
                )),
                ('fulfills_request', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='pending_approval', to='documents.documentrequest',
                )),
            ],
            options={'ordering': ['-created_at']},
        ),
    ]
