import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("datasets", "0003_organization_required"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]

    operations = [
        migrations.AddField(model_name="dataset", name="analysis_results", field=models.JSONField(blank=True, default=dict)),
        migrations.AddIndex(model_name="dataset", index=models.Index(fields=["organization", "created_at"], name="dataset_org_created_idx")),
        migrations.CreateModel(name="DatasetProcessingJob", fields=[
            ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
            ("status", models.CharField(choices=[("queued", "Queued"), ("processing", "Processing"), ("completed", "Completed"), ("failed", "Failed"), ("cancelled", "Cancelled")], default="queued", max_length=20)),
            ("progress", models.PositiveSmallIntegerField(default=0)), ("error_message", models.TextField(blank=True)),
            ("started_at", models.DateTimeField(blank=True, null=True)), ("completed_at", models.DateTimeField(blank=True, null=True)), ("created_at", models.DateTimeField(auto_now_add=True)),
            ("dataset", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="processing_jobs", to="datasets.dataset")),
            ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="dataset_jobs", to="organizations.organization")),
        ]),
        migrations.CreateModel(name="AnalyticsEvent", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("event_type", models.CharField(max_length=64)), ("metadata", models.JSONField(blank=True, default=dict)), ("created_at", models.DateTimeField(auto_now_add=True)),
            ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="analytics_events", to="organizations.organization")), ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="analytics_events", to=settings.AUTH_USER_MODEL)),
        ]),
        migrations.CreateModel(name="WeeklyReport", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("period_start", models.DateTimeField()), ("period_end", models.DateTimeField()), ("generated_at", models.DateTimeField(blank=True, null=True)), ("status", models.CharField(choices=[("generating", "Generating"), ("completed", "Completed"), ("failed", "Failed")], default="generating", max_length=20)), ("report_data", models.JSONField(default=dict)), ("error_message", models.TextField(blank=True)),
            ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="weekly_reports", to="organizations.organization")),
        ]),
        migrations.CreateModel(name="WeeklyReportDelivery", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("recipient", models.EmailField(max_length=254)), ("status", models.CharField(choices=[("queued", "Queued"), ("sent", "Sent"), ("failed", "Failed")], default="queued", max_length=20)), ("sent_at", models.DateTimeField(blank=True, null=True)), ("error_message", models.TextField(blank=True)),
            ("report", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="deliveries", to="datasets.weeklyreport")),
        ]),
        migrations.AddIndex(model_name="datasetprocessingjob", index=models.Index(fields=["organization", "status"], name="datasets_da_org_sta_idx")), migrations.AddIndex(model_name="datasetprocessingjob", index=models.Index(fields=["dataset", "created_at"], name="datasets_da_dat_cre_idx")),
        migrations.AddIndex(model_name="analyticsevent", index=models.Index(fields=["organization", "created_at"], name="datasets_an_org_cre_idx")), migrations.AddIndex(model_name="analyticsevent", index=models.Index(fields=["organization", "event_type", "created_at"], name="datasets_an_org_eve_idx")), migrations.AddIndex(model_name="weeklyreport", index=models.Index(fields=["organization", "period_start"], name="datasets_we_org_per_idx")),
        migrations.AddConstraint(model_name="weeklyreport", constraint=models.UniqueConstraint(fields=("organization", "period_start", "period_end"), name="unique_weekly_report_period")), migrations.AddConstraint(model_name="weeklyreportdelivery", constraint=models.UniqueConstraint(fields=("report", "recipient"), name="unique_report_recipient")),
    ]
