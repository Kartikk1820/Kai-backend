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
