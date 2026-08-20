import logging
from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from core.permissions import IsOrganizationMember, IsOwnerOrAdmin
from .models import Dataset
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
        process_dataset_async.delay(str(dataset.id))

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
