from django.contrib import admin
from .models import Organization


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "plan", "member_count", "is_active", "created_at")
    list_filter = ("plan", "is_active")
    search_fields = ("name", "slug")
    readonly_fields = ("id", "created_at", "updated_at", "member_count")
    prepopulated_fields = {"slug": ("name",)}

    fieldsets = (
        (None, {"fields": ("id", "name", "slug", "plan", "is_active")}),
        ("Limits", {"fields": ("max_users", "max_datasets")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )
