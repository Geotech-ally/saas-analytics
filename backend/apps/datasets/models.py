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
    allowed_extensions = [".csv", ".xlsx", ".xls"]
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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "datasets"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["uploaded_by"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.organization})"
