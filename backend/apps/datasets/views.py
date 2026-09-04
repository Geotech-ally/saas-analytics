import logging
from datetime import timedelta
from django.core.cache import cache
from django.db.models import Count
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework.views import APIView

from core.permissions import IsOrganizationMember, IsOwnerOrAdmin
from .models import AnalyticsEvent, Dataset, DatasetProcessingJob, WeeklyReport
from .serializers import DatasetSerializer
from .tasks import process_dataset_async

logger = logging.getLogger(__name__)


class DatasetViewSet(ModelViewSet):
    queryset = Dataset.objects.select_related("organization", "uploaded_by").all()
    serializer_class = DatasetSerializer
    permission_classes = [permissions.IsAuthenticated, IsOrganizationMember]

    def get_queryset(self):
        user = self.request.user
        qs = Dataset.objects.filter(organization=user.organization)
        dataset_id = self.request.query_params.get("id")
        if dataset_id:
            try:
                from uuid import UUID
                qs = qs.filter(id=UUID(dataset_id))
            except (ValueError, TypeError):
                qs = qs.none()
        return qs

    def get_permissions(self):
        if self.action in ["update", "partial_update", "destroy"]:
            return [permissions.IsAuthenticated(), IsOwnerOrAdmin()]
        return super().get_permissions()

    def perform_create(self, serializer):
        dataset = serializer.save()
        job = DatasetProcessingJob.objects.create(organization=dataset.organization, dataset=dataset)
        AnalyticsEvent.objects.create(organization=dataset.organization, user=self.request.user, event_type="dataset_uploaded", metadata={"dataset_id": str(dataset.id)})
        process_dataset_async.delay(str(job.id))

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        if response.status_code == status.HTTP_201_CREATED:
            dataset = Dataset.objects.get(id=response.data["id"], organization=request.user.organization)
            job = dataset.processing_jobs.order_by("-created_at").first()
            response.data["job_id"] = str(job.id) if job else None
            response.data["processing_status"] = job.status if job else "queued"
        return response

    @action(detail=True, methods=["get"])
    def analytics(self, request, pk=None):
        dataset = self.get_object()
        if dataset.status != Dataset.Status.READY:
            return Response(
                {"detail": "Dataset is not yet ready for analysis."},
                status=status.HTTP_202_ACCEPTED,
            )
        try:
            from core.fastapi_client import FastAPIClient

            client = FastAPIClient(user=request.user)
            data = client.get_analytics(dataset_id=str(dataset.id))
            return Response(data)
        except Exception as exc:
            logger.error("Analytics fetch failed for dataset %s: %s", dataset.id, exc)
            return Response(
                {"detail": "Analytics service unavailable. Please try again."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

    @action(detail=True, methods=["get"])
    def insights(self, request, pk=None):
        dataset = self.get_object()
        try:
            from core.fastapi_client import FastAPIClient

            client = FastAPIClient(user=request.user)
            data = client.get_insights(dataset_id=str(dataset.id))
            return Response(data)
        except Exception as exc:
            logger.error("Insights fetch failed: %s", exc)
            return Response(
                {"detail": "Analytics service unavailable."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

    @action(detail=True, methods=["get"])
    def jobs(self, request, pk=None):
        dataset = self.get_object()
        jobs = dataset.processing_jobs.filter(organization=request.user.organization).values(
            "id", "status", "progress", "started_at", "completed_at", "created_at"
        )
        return Response(list(jobs))


class LiveAnalyticsView(APIView):
    """Small, cached, organization-scoped current-usage aggregate."""
    permission_classes = [permissions.IsAuthenticated, IsOrganizationMember]

    def get(self, request):
        org = request.user.organization
        key = f"analytics:{org.id}:live"
        payload = cache.get(key)
        if payload is None:
            now = timezone.now(); hour = now - timedelta(hours=1); day = now - timedelta(days=1)
            events = AnalyticsEvent.objects.filter(organization=org)
            payload = {
                "active_users": events.filter(created_at__gte=hour).exclude(user__isnull=True).values("user_id").distinct().count(),
                "requests_per_minute": round(events.filter(created_at__gte=hour).count() / 60, 2),
                "events_today": events.filter(created_at__gte=day).count(),
                "datasets_processing": DatasetProcessingJob.objects.filter(organization=org, status__in=["queued", "processing"]).count(),
                "datasets_completed_today": Dataset.objects.filter(organization=org, status=Dataset.Status.READY, updated_at__gte=day).count(),
                "top_features": list(events.filter(created_at__gte=day).values("event_type").annotate(count=Count("id")).order_by("-count")[:5]),
            }
            cache.set(key, payload, 30)
        return Response(payload)


class WeeklyReportViewSet(ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAuthenticated, IsOrganizationMember]

    def list(self, request, *args, **kwargs):
        reports = WeeklyReport.objects.filter(organization=request.user.organization).order_by("-period_start")
        return Response([{"id": str(r.id), "period_start": r.period_start, "period_end": r.period_end, "generated_at": r.generated_at, "status": r.status, "report_data": r.report_data} for r in reports])

    def retrieve(self, request, *args, **kwargs):
        report = WeeklyReport.objects.get(pk=kwargs["pk"], organization=request.user.organization)
        return Response({"id": str(report.id), "period_start": report.period_start, "period_end": report.period_end, "generated_at": report.generated_at, "status": report.status, "report_data": report.report_data})
