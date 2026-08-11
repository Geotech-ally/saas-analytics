import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("organizations", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Dataset",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                ("file", models.FileField(upload_to="datasets/%Y/%m/")),
                ("file_size", models.PositiveIntegerField(default=0)),
                ("row_count", models.PositiveIntegerField(blank=True, null=True)),
                ("column_count", models.PositiveIntegerField(blank=True, null=True)),
                ("status", models.CharField(
                    choices=[
                        ("pending", "Pending"), ("processing", "Processing"),
                        ("ready", "Ready"), ("failed", "Failed"),
                    ],
                    default="pending", max_length=20,
                )),
                ("error_message", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("organization", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="datasets",
                    to="organizations.organization",
                )),
                ("uploaded_by", models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="uploaded_datasets",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={"db_table": "datasets", "ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="dataset",
            index=models.Index(fields=["organization", "status"], name="dataset_org_status_idx"),
        ),
        migrations.AddIndex(
            model_name="dataset",
            index=models.Index(fields=["uploaded_by"], name="dataset_uploader_idx"),
        ),
    ]
