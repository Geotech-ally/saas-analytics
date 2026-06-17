from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from core.permissions import IsOrganizationAdmin, IsSameOrganization
from .models import Organization
from .serializers import OrganizationSerializer, OrganizationCreateSerializer


class OrganizationViewSet(ModelViewSet):
    queryset = Organization.objects.filter(is_active=True)
    permission_classes = [permissions.IsAuthenticated, IsSameOrganization]

    def get_serializer_class(self):
        if self.action == "create":
            return OrganizationCreateSerializer
        return OrganizationSerializer

    def get_permissions(self):
        if self.action in ["update", "partial_update", "destroy"]:
            return [permissions.IsAuthenticated(), IsOrganizationAdmin()]
        return super().get_permissions()

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return self.queryset
        return self.queryset.filter(id=user.organization_id)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = False
        instance.save(update_fields=["is_active"])
        return Response(status=status.HTTP_204_NO_CONTENT)
