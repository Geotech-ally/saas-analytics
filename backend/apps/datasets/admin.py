from django.contrib import admin
from .models import Dataset


@admin.register(Dataset)
class DatasetAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "uploaded_by", "status", "file_size_kb", "created_at")
    list_filter = ("status", "organization")
    search_fields = ("name", "uploaded_by__email", "organization__name")
    readonly_fields = ("id", "file_size", "row_count", "column_count", "created_at", "updated_at")

    fieldsets = (
        (None, {"fields": ("id", "name", "description", "organization", "uploaded_by")}),
        ("File", {"fields": ("file", "file_size", "row_count", "column_count")}),
        ("Processing", {"fields": ("status", "error_message")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    @admin.display(description="Size (KB)")
    def file_size_kb(self, obj):
        return f"{obj.file_size / 1024:.1f} KB" if obj.file_size else "—"
