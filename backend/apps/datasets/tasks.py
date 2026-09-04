"""Tenant-scoped, retryable background work."""
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db.models import Count
from django.utils import timezone
from .models import AnalyticsEvent, Dataset, DatasetProcessingJob, WeeklyReport, WeeklyReportDelivery

logger = logging.getLogger(__name__)

def _summary(dataset):
    import pandas as pd
    ext = dataset.file.name.rsplit('.', 1)[-1].lower()
    if ext == 'csv': frame = pd.read_csv(dataset.file.path, nrows=500000)
    elif ext in {'xls', 'xlsx'}: frame = pd.read_excel(dataset.file.path, nrows=500000)
    elif ext == 'json': frame = pd.read_json(dataset.file.path).head(500000)
    else: raise ValueError('Unsupported dataset format')
    if frame.empty: raise ValueError('Dataset is empty')
    columns = [{"name": str(name), "dtype": str(frame[name].dtype), "missing": int(frame[name].isna().sum()), "unique": int(frame[name].nunique())} for name in frame.columns]
    return len(frame), len(frame.columns), {"columns": columns, "duplicate_rows": int(frame.duplicated().sum())}

@shared_task(bind=True, max_retries=3)
def process_dataset_async(self, job_id):
    try: job = DatasetProcessingJob.objects.select_related('dataset', 'organization', 'dataset__uploaded_by').get(id=job_id)
    except DatasetProcessingJob.DoesNotExist: return
    if job.status == DatasetProcessingJob.Status.COMPLETED: return {"job_id": str(job.id), "status": job.status}
    dataset = job.dataset
    job.status, job.progress, job.started_at = DatasetProcessingJob.Status.PROCESSING, 10, job.started_at or timezone.now()
    job.save(update_fields=['status', 'progress', 'started_at'])
    dataset.status = Dataset.Status.PROCESSING; dataset.save(update_fields=['status', 'updated_at'])
    try:
        rows, cols, results = _summary(dataset)
        dataset.row_count, dataset.column_count, dataset.analysis_results, dataset.status, dataset.error_message = rows, cols, results, Dataset.Status.READY, ''
        dataset.save(update_fields=['row_count', 'column_count', 'analysis_results', 'status', 'error_message', 'updated_at'])
        job.status, job.progress, job.completed_at = DatasetProcessingJob.Status.COMPLETED, 100, timezone.now()
        job.save(update_fields=['status', 'progress', 'completed_at'])
        AnalyticsEvent.objects.create(organization=job.organization, user=dataset.uploaded_by, event_type='dataset_processing_completed', metadata={'dataset_id': str(dataset.id), 'job_id': str(job.id)})
        return {"job_id": str(job.id), "status": job.status}
    except Exception as exc:
        logger.warning('Dataset processing failed job=%s: %s', job.id, type(exc).__name__)
        if self.request.retries < self.max_retries: raise self.retry(exc=exc, countdown=30 * (2 ** self.request.retries))
        dataset.status, dataset.error_message = Dataset.Status.FAILED, 'Processing failed.'; dataset.save(update_fields=['status', 'error_message', 'updated_at'])
        job.status, job.error_message, job.completed_at = DatasetProcessingJob.Status.FAILED, 'Processing failed.', timezone.now(); job.save(update_fields=['status', 'error_message', 'completed_at'])
        raise

def previous_complete_week(now=None):
    local = (now or timezone.now()).astimezone(ZoneInfo(settings.WEEKLY_REPORT_TIMEZONE))
    end = (local - timedelta(days=local.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    return end - timedelta(days=7), end

def _metrics(org, start, end):
    events = AnalyticsEvent.objects.filter(organization=org, created_at__gte=start, created_at__lt=end); datasets = Dataset.objects.filter(organization=org, created_at__gte=start, created_at__lt=end)
    return {'active_users': events.exclude(user__isnull=True).values('user_id').distinct().count(), 'events': events.count(), 'datasets_uploaded': datasets.count(), 'datasets_completed': datasets.filter(status=Dataset.Status.READY).count(), 'datasets_failed': datasets.filter(status=Dataset.Status.FAILED).count(), 'top_features': list(events.values('event_type').annotate(count=Count('id')).order_by('-count')[:5])}

@shared_task(bind=True, max_retries=3)
def generate_weekly_report(self, organization_id, period_start=None, period_end=None):
    from apps.organizations.models import Organization
    org = Organization.objects.get(id=organization_id, is_active=True); start, end = previous_complete_week() if not period_start else (datetime.fromisoformat(period_start), datetime.fromisoformat(period_end))
    report, _ = WeeklyReport.objects.get_or_create(organization=org, period_start=start, period_end=end)
    if report.status == WeeklyReport.Status.COMPLETED: return str(report.id)
    report.report_data = {'metrics': _metrics(org, start, end), 'previous_period': _metrics(org, start - (end-start), start), 'period_start': start.isoformat(), 'period_end': end.isoformat()}; report.status, report.generated_at = WeeklyReport.Status.COMPLETED, timezone.now(); report.save(update_fields=['report_data', 'status', 'generated_at']); send_weekly_report_email.delay(str(report.id)); return str(report.id)

@shared_task
def send_weekly_analytics_report():
    from apps.organizations.models import Organization
    start, end = previous_complete_week()
    for org_id in Organization.objects.filter(is_active=True).values_list('id', flat=True): generate_weekly_report.delay(str(org_id), start.isoformat(), end.isoformat())

@shared_task(bind=True, max_retries=3)
def send_weekly_report_email(self, report_id):
    from apps.users.models import User
    report = WeeklyReport.objects.select_related('organization').get(id=report_id, status=WeeklyReport.Status.COMPLETED)
    for email in User.objects.filter(organization=report.organization, is_active=True, role=User.Role.ADMIN).values_list('email', flat=True):
        delivery, _ = WeeklyReportDelivery.objects.get_or_create(report=report, recipient=email)
        if delivery.status == WeeklyReportDelivery.Status.SENT: continue
        try:
            message = EmailMultiAlternatives(f'DataLens Weekly Report — {report.organization.name}', 'Your weekly analytics report is ready.', settings.DEFAULT_FROM_EMAIL, [email]); message.attach_alternative('<h1>Weekly Analytics Report</h1><p>Your dashboard contains the full report.</p>', 'text/html'); message.send(); delivery.status, delivery.sent_at, delivery.error_message = WeeklyReportDelivery.Status.SENT, timezone.now(), ''; delivery.save(update_fields=['status', 'sent_at', 'error_message'])
        except Exception as exc:
            delivery.status, delivery.error_message = WeeklyReportDelivery.Status.FAILED, 'Email delivery failed.'; delivery.save(update_fields=['status', 'error_message']); raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
