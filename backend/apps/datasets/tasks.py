import logging
from datetime import datetime, timedelta

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.db.models import Count, Sum, Avg, Max, Min
from django.utils import timezone

from .models import Dataset

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def process_dataset_async(self, dataset_id):
    """Background task to process an uploaded dataset through FastAPI."""
    try:
        dataset = Dataset.objects.get(id=dataset_id)
    except Dataset.DoesNotExist:
        logger.warning("Dataset %s not found, skipping processing.", dataset_id)
        return

    if dataset.organization_id is None:
        logger.error(
            "Dataset %s has no organization; cannot process.", dataset_id
        )
        dataset.status = Dataset.Status.FAILED
        dataset.error_message = "Dataset has no organization assigned."
        dataset.save(update_fields=["status", "error_message"])
        return

    if dataset.uploaded_by is None:
        logger.error(
            "Dataset %s has no uploaded_by user; cannot process.", dataset_id
        )
        dataset.status = Dataset.Status.FAILED
        dataset.error_message = "Dataset has no uploaded user."
        dataset.save(update_fields=["status", "error_message"])
        return

    dataset.status = Dataset.Status.PROCESSING
    dataset.save(update_fields=["status"])

    try:
        from core.fastapi_client import FastAPIClient

        client = FastAPIClient(user=dataset.uploaded_by)
        response = client.trigger_processing(dataset_id=str(dataset.id))
        logger.info(
            "FastAPI triggered processing for dataset %s: %s", dataset_id, response
        )
    except Exception as exc:
        logger.error(
            "FastAPI processing trigger failed for dataset %s: %s", dataset_id, exc
        )
        dataset.status = Dataset.Status.FAILED
        dataset.error_message = str(exc)
        dataset.save(update_fields=["status", "error_message"])
        raise self.retry(exc=exc)


@shared_task
def generate_analytics_async(dataset_id):
    """Background task to generate analytics for a processed dataset."""
    try:
        dataset = Dataset.objects.get(id=dataset_id)
    except Dataset.DoesNotExist:
        logger.warning("Dataset %s not found for analytics.", dataset_id)
        return

    logger.info("Analytics generation started for dataset %s", dataset_id)
    return {"dataset_id": str(dataset_id), "status": "analytics_queue"}


@shared_task
def send_weekly_analytics_report():
    """Send weekly analytics report to all active users."""
    from apps.users.models import User
    from django.db.models import Q

    now = timezone.now()
    week_start = now - timedelta(days=7)

    active_users = User.objects.filter(
        is_active=True,
        organization__isnull=False,
        organization__is_active=True,
    ).select_related("organization")

    sent_count = 0
    failed_count = 0

    for user in active_users:
        try:
            org_datasets = Dataset.objects.filter(
                organization=user.organization,
                created_at__gte=week_start,
            )
            total_datasets = org_datasets.count()
            ready_datasets = org_datasets.filter(status=Dataset.Status.READY).count()
            processing_datasets = org_datasets.filter(status=Dataset.Status.PROCESSING).count()
            failed_datasets = org_datasets.filter(status=Dataset.Status.FAILED).count()
            total_size = sum(d.file_size for d in org_datasets) / (1024 * 1024)

            subject = f"DataLens Weekly Report — {user.organization.name}"
            message = f"""Hello {user.full_name},

Here is your weekly analytics report for {user.organization.name}:

Week: {week_start.strftime('%Y-%m-%d')} to {now.strftime('%Y-%m-%d')}

Summary:
- Total datasets uploaded: {total_datasets}
- Ready for analysis: {ready_datasets}
- Currently processing: {processing_datasets}
- Failed: {failed_datasets}
- Total storage used: {total_size:.2f} MB

Log in to your dashboard for detailed analytics.

Best regards,
DataLens Team"""

            send_mail(
                subject,
                message,
                getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@datalens.com"),
                [user.email],
                fail_silently=False,
            )
            logger.info("Weekly report sent to %s", user.email)
            sent_count += 1
        except Exception as exc:
            logger.error("Failed to send weekly report to %s: %s", user.email, exc)
            failed_count += 1

    logger.info("Weekly analytics report task completed: sent=%d failed=%d", sent_count, failed_count)
    return {"sent": sent_count, "failed": failed_count}
