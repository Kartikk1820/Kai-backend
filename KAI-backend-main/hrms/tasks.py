"""HRMS Celery tasks: scheduled salary run (1st) and incentive dispatch (15th)."""
from celery import shared_task
from django.utils import timezone
import structlog

logger = structlog.get_logger(__name__)


@shared_task
def run_monthly_salary():
    """On the 1st, run salary for the PREVIOUS month (arrears)."""
    from .services import PayrollService
    today = timezone.localdate()
    # previous month
    year = today.year
    month = today.month - 1
    if month == 0:
        month, year = 12, year - 1
    run = PayrollService.run_salary(month=month, year=year, user=None)
    logger.info('monthly_salary_run', month=month, year=year, count=run.records_generated)
    return {'run_id': run.id, 'count': run.records_generated}


@shared_task
def dispatch_scheduled_incentives():
    """On the 15th, send all scheduled incentives for the current month."""
    from .models import Incentive
    from .services import IncentiveService
    today = timezone.localdate()
    qs = Incentive.objects.filter(status='scheduled', month=today.month, year=today.year)
    sent = 0
    for inc in qs:
        IncentiveService.send(inc.id, system=True)
        sent += 1
    logger.info('incentives_dispatched', month=today.month, year=today.year, sent=sent)
    return {'sent': sent}


@shared_task
def notify_eight_hours_reached(user_id, date_str):
    """Sends a notification to the user after they have reached 8 hours of work."""
    from .models import Attendance
    from notifications.services import notify
    from django.contrib.auth import get_user_model
    import datetime
    
    User = get_user_model()
    try:
        user = User.objects.get(id=user_id)
        # Verify they actually worked 8 hours (in case they clocked out early and this task was left running)
        date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        att = Attendance.objects.filter(employee_id=user_id, date=date).first()
        if att and att.working_hours >= 7.9:
            notify(user=user, kind='attendance_8_hours',
                   title='Great job today!',
                   body='You have reached 8 hours of work today. You can clock out now if your shift is over.',
                   link='/hrms', actor=user)
    except Exception as e:
        logger.error('failed_to_send_8hr_notification', error=str(e))


@shared_task
def auto_clock_out_midnight():
    """Clock out any active sessions at midnight (23:59:59)."""
    from .models import AttendanceSession
    from django.utils import timezone
    import datetime
    
    # Run slightly before midnight or just look at all nulls
    active_sessions = AttendanceSession.objects.filter(clock_out_time__isnull=True)
    count = active_sessions.count()
    for session in active_sessions:
        session.clock_out_time = datetime.time(23, 59, 59)
        session.save()
        
    logger.info('auto_clocked_out_midnight', count=count)
    return {'closed': count}
