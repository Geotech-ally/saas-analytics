import logging
from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.tokens import AccessToken

from core.permissions import IsOrganizationMember, IsOwnerOrAdmin, IsSameOrganization
from core.fastapi_client import FastAPIClient
from .models import Dataset
from .serializers import DatasetSerializer

logger = logging.getLogger(__name__)


class DatasetViewSet(ModelViewSet):
    queryset = Dataset.objects.select_related("organization", "uploaded_by").all()
    serializer_class = DatasetSerializer
    permission_classes = [permissions.IsAuthenticated, IsOrganizationMember]

    def get_queryset(self):
        user = self.request.user
        return self.queryset.filter(organization=user.organization)

    def get_permissions(self):
        if self.action in ["destroy"]:
            return [permissions.IsAuthenticated(), IsOwnerOrAdmin()]
        return super().get_permissions()

    def perform_create(self, serializer):
        dataset = serializer.save()
        # Trigger async processing via FastAPI
        try:
            client = FastAPIClient(user=self.request.user)
            client.trigger_processing(dataset_id=str(dataset.id))
        except Exception as exc:
            logger.warning("FastAPI trigger failed for dataset %s: %s", dataset.id, exc)

    @action(detail=True, methods=["get"])
    def analytics(self, request, pk=None):
        """Proxy analytics request to FastAPI service."""
        dataset = self.get_object()
        if dataset.status != Dataset.Status.READY:
            return Response(
                {"detail": "Dataset is not yet ready for analysis."},
                status=status.HTTP_202_ACCEPTED,
            )
        try:
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
        """Proxy insights request to FastAPI service."""
        dataset = self.get_object()
        try:
            client = FastAPIClient(user=request.user)
            data = client.get_insights(dataset_id=str(dataset.id))
            return Response(data)
        except Exception as exc:
            logger.error("Insights fetch failed: %s", exc)
            return Response(
                {"detail": "Analytics service unavailable."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
