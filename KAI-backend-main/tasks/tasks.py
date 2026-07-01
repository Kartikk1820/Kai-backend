from celery import shared_task
from datetime import date


@shared_task
def spawn_recurring_tasks():
    """Daily task: clone each active recurrence template if today matches its schedule."""
    from .models import Task

    today = date.today()
    dow = today.weekday()          # 0=Mon … 6=Sun
    dom = today.day                # 1–31
    mmdd = today.strftime('%m-%d') # "01-15"

    templates = (
        Task.objects
        .filter(is_recurrence_template=True)
        .exclude(status='done')
        .select_related('assignee', 'reporter', 'team', 'linked_bid')
    )

    for t in templates:
        if t.recurrence_end_date and today > t.recurrence_end_date:
            continue

        match = False
        if t.recurrence_type == 'daily':
            match = True
        elif t.recurrence_type == 'weekly':
            match = dow in (t.recurrence_days or [])
        elif t.recurrence_type == 'monthly':
            match = dom in (t.recurrence_days or [])
        elif t.recurrence_type == 'yearly':
            match = mmdd in (t.recurrence_days or [])

        if not match:
            continue

        if t.spawned_instances.filter(created_at__date=today).exists():
            continue

        Task.objects.create(
            title=t.title,
            description=t.description,
            priority=t.priority,
            task_type=t.task_type,
            story_points=t.story_points,
            assignee=t.assignee,
            reporter=t.reporter,
            team=t.team,
            linked_bid=t.linked_bid,
            labels=list(t.labels or []),
            start_date=today,
            recurrence_parent=t,
            is_recurrence_template=False,
            recurrence_type='none',
        )
