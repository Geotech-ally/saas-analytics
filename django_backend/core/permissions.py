from rest_framework.permissions import BasePermission, SAFE_METHODS
from apps.users.models import User


class IsOrganizationAdmin(BasePermission):
    """Allow access only to org-level admins."""
    message = "You must be an organization admin to perform this action."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == User.Role.ADMIN
        )


class IsOrganizationMember(BasePermission):
    """Allow access to any authenticated member of an organization."""
    message = "You must belong to an organization to perform this action."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.organization_id is not None
        )


class IsAdminOrReadOnly(BasePermission):
    """Admins get full access; regular users get read-only."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return request.user.role == User.Role.ADMIN


class IsSameOrganization(BasePermission):
    """Object-level: only allow access to objects in the user's own org."""
    message = "You do not have access to this resource."

    def has_object_permission(self, request, view, obj):
        # obj must have an `organization` attribute
        org_id = getattr(obj, "organization_id", None)
        if org_id is None:
            # obj IS an organization
            org_id = getattr(obj, "id", None)
        return str(org_id) == str(request.user.organization_id)


class IsOwnerOrAdmin(BasePermission):
    """Object-level: allow access to owners or org admins."""
    message = "You do not have permission to modify this resource."

    def has_object_permission(self, request, view, obj):
        if request.user.role == User.Role.ADMIN:
            return True
        owner = getattr(obj, "uploaded_by", None) or getattr(obj, "id", None)
        owner_id = getattr(owner, "id", owner)
        return str(owner_id) == str(request.user.id)
