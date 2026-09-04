import uuid
import os
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError


def dataset_upload_path(instance, filename):
    if not instance.id:
        return f"datasets/{instance.organization_id}/temp/{filename}"
    return f"datasets/{instance.organization_id}/{instance.id}/{filename}"


def validate_file_extension(value):
    ext = os.path.splitext(value.name)[1].lower()
    allowed_extensions = [".csv", ".xlsx", ".xls", ".json"]
    if ext not in allowed_extensions:
        raise ValidationError(f"Unsupported file extension '{ext}'. Allowed: {', '.join(allowed_extensions)}")


class Dataset(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        READY = "ready", "Ready"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey("organizations.Organization", on_delete=models.CASCADE, related_name="datasets")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="uploaded_datasets",
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to=dataset_upload_path, validators=[validate_file_extension])
    file_size = models.PositiveIntegerField(default=0)
    row_count = models.PositiveIntegerField(null=True, blank=True)
    column_count = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    error_message = models.TextField(blank=True)
    analysis_results = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "datasets"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["uploaded_by"]),
            models.Index(fields=["organization", "created_at"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.organization})"


class DatasetProcessingJob(models.Model):
    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey("organizations.Organization", on_delete=models.CASCADE, related_name="dataset_jobs")
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name="processing_jobs")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.QUEUED)
    progress = models.PositiveSmallIntegerField(default=0)
    error_message = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["organization", "status"]), models.Index(fields=["dataset", "created_at"])]


class AnalyticsEvent(models.Model):
    organization = models.ForeignKey("organizations.Organization", on_delete=models.CASCADE, related_name="analytics_events")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="analytics_events")
    event_type = models.CharField(max_length=64)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["organization", "created_at"]), models.Index(fields=["organization", "event_type", "created_at"])]


class WeeklyReport(models.Model):
    class Status(models.TextChoices):
        GENERATING = "generating", "Generating"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
    organization = models.ForeignKey("organizations.Organization", on_delete=models.CASCADE, related_name="weekly_reports")
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    generated_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.GENERATING)
    report_data = models.JSONField(default=dict)
    error_message = models.TextField(blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["organization", "period_start", "period_end"], name="unique_weekly_report_period")]
        indexes = [models.Index(fields=["organization", "period_start"])]


class WeeklyReportDelivery(models.Model):
    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"
    report = models.ForeignKey(WeeklyReport, on_delete=models.CASCADE, related_name="deliveries")
    recipient = models.EmailField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.QUEUED)
    sent_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["report", "recipient"], name="unique_report_recipient")]
