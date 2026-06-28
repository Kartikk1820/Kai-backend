"""HRMS Celery tasks."""
from celery import shared_task
from django.utils import timezone
import structlog

logger = structlog.get_logger(__name__)


@shared_task
def seed_monthly_calendar():
    """
    1st of month at 00:30 — pre-create Attendance rows for holidays and weekly-offs
    for the current month so the attendance view shows correct status for non-working days.
    """
    from .services import AttendanceService
    today = timezone.localdate()
    AttendanceService.seed_calendar(month=today.month, year=today.year)
    logger.info('calendar_seeded', month=today.month, year=today.year)
    return {'month': today.month, 'year': today.year}


@shared_task
def run_monthly_salary():
    """1st of month at 02:00 — run salary for the previous month."""
    from .services import PayrollService
    today = timezone.localdate()
    year, month = today.year, today.month - 1
    if month == 0:
        month, year = 12, year - 1
    run = PayrollService.run_salary(month=month, year=year, user=None)
    logger.info('monthly_salary_run', month=month, year=year,
                count=run.records_generated, errors=len(run.errors))
    return {'run_id': run.id, 'count': run.records_generated, 'errors': len(run.errors)}


@shared_task
def dispatch_scheduled_incentives():
    """15th of month at 02:00 — send all scheduled incentives for this month."""
    from .models import Incentive
    from .services import IncentiveService
    today = timezone.localdate()
    qs = Incentive.objects.filter(status='scheduled', month=today.month, year=today.year)
    sent = 0
    for inc in qs:
        try:
            IncentiveService.send(inc.id, system=True)
            sent += 1
        except Exception as e:
            logger.error('incentive_send_failed', incentive_id=inc.id, error=str(e))
    logger.info('incentives_dispatched', month=today.month, year=today.year, sent=sent)
    return {'sent': sent}


@shared_task
def notify_eight_hours_reached(user_id, date_str):
    """Notify user after they reach 8 hours of work."""
    from .models import Attendance
    from notifications.services import notify
    from django.contrib.auth import get_user_model
    import datetime

    User = get_user_model()
    try:
        user = User.objects.get(id=user_id)
        d = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        att = Attendance.objects.filter(employee_id=user_id, date=d).first()
        if att and att.working_hours >= 7.9:
            notify(user=user, kind='attendance_8_hours',
                   title='Great job today!',
                   body='You have reached 8 hours of work today.',
                   link='/hrms', actor=user)
    except Exception as e:
        logger.error('failed_to_send_8hr_notification', error=str(e))


@shared_task
def auto_clock_out_midnight():
    """Clock out any active sessions at 23:59:59."""
    from .models import AttendanceSession
    import datetime

    active_sessions = AttendanceSession.objects.filter(clock_out_time__isnull=True)
    count = active_sessions.count()
    for session in active_sessions:
        session.clock_out_time = datetime.time(23, 59, 59)
        session.save()
    logger.info('auto_clocked_out_midnight', count=count)
    return {'closed': count}
