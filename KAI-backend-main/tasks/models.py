from django.db import models
from django.conf import settings
from django.db import transaction
from django_fsm import FSMField, transition


class Team(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=255, blank=True)
    lead = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='led_teams',
    )
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name='teams',
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class TaskKeyCounter(models.Model):
    """Single-row counter that produces sequential task keys (KAI-1, KAI-2, ...)."""
    prefix = models.CharField(max_length=10, primary_key=True)
    last_number = models.PositiveIntegerField(default=0)

    @classmethod
    def next_key(cls, prefix):
        with transaction.atomic():
            counter, _ = cls.objects.select_for_update().get_or_create(prefix=prefix)
            counter.last_number += 1
            counter.save(update_fields=['last_number'])
            return f"{prefix}-{counter.last_number}"


class Task(models.Model):
    STATUS = [
        ('todo', 'To Do'),
        ('in_progress', 'In Progress'),
        ('blocked', 'Blocked'),
        ('review', 'Review'),
        ('done', 'Completed'),
    ]
    PRIORITY = [
        ('highest', 'Highest'),
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
        ('lowest', 'Lowest'),
    ]

    key = models.CharField(max_length=20, unique=True, editable=False, db_index=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = FSMField(default='todo', choices=STATUS, protected=True, db_index=True)
    priority = models.CharField(max_length=10, choices=PRIORITY, default='medium', db_index=True)

    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='assigned_tasks', db_index=True,
    )
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='reported_tasks',
    )
    team = models.ForeignKey(
        Team, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='tasks', db_index=True,
    )
    linked_bid = models.ForeignKey(
        'bids.ClientBid', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='tasks',
    )

    labels = models.JSONField(default=list, blank=True)
    start_date = models.DateField(null=True, blank=True)
    due_date = models.DateTimeField(null=True, blank=True, db_index=True)

    # Fractional ordering within a column.
    position = models.FloatField(default=0)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='created_tasks',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['position', '-created_at']
        indexes = [
            models.Index(fields=['status', 'position']),
            models.Index(fields=['assignee', 'status']),
        ]

    def __str__(self):
        return f"{self.key} — {self.title}"

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = TaskKeyCounter.next_key(settings.TASK_KEY_PREFIX)
        super().save(*args, **kwargs)

    # ----- FSM transitions (called only by the service layer) -----
    @transition(field=status, source='todo', target='in_progress')
    def start(self):
        pass

    @transition(field=status, source='in_progress', target='review')
    def submit_for_review(self):
        pass

    @transition(field=status, source='review', target='done')
    def approve(self):
        pass

    @transition(field=status, source='review', target='in_progress')
    def send_back(self):
        pass

    @transition(field=status, source=['todo', 'in_progress', 'review'], target='blocked')
    def block(self):
        pass

    @transition(field=status, source='blocked', target='todo')
    def unblock(self):
        pass

    @transition(field=status, source='done', target='review')
    def reopen(self):
        pass

    @transition(field=status, source='*', target='todo')
    def force_todo(self):
        pass

    @transition(field=status, source='*', target='in_progress')
    def force_in_progress(self):
        pass

    @transition(field=status, source='*', target='review')
    def force_review(self):
        pass

    @transition(field=status, source='*', target='blocked')
    def force_blocked(self):
        pass

    @transition(field=status, source='*', target='done')
    def force_done(self):
        pass


class Comment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='task_comments')
    body = models.TextField()
    is_edited = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.author_id} on {self.task_id}"


def attachment_path(instance, filename):
    return f"task_attachments/{instance.task_id}/{filename}"


class Attachment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to=attachment_path)
    filename = models.CharField(max_length=255)
    size = models.PositiveIntegerField(default=0)
    content_type = models.CharField(max_length=120, blank=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return self.filename


class TaskLink(models.Model):
    RELATION = [
        ('relates_to', 'relates to'),
        ('blocks', 'blocks'),
        ('is_blocked_by', 'is blocked by'),
    ]
    source_task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='outgoing_links')
    target_task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='incoming_links')
    relation = models.CharField(max_length=20, choices=RELATION)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('source_task', 'target_task', 'relation')

    def __str__(self):
        return f"{self.source_task_id} {self.relation} {self.target_task_id}"
