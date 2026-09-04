import os
import logging
from rest_framework import serializers
from .models import Dataset

logger = logging.getLogger(__name__)


def _sanitize_filename(filename: str) -> str:
    name = os.path.basename(filename)
    name = name.replace("\\", "_").replace("/", "_").replace("..", "_")
    return name


def _validate_file_magic(value):
    header = value.read(8)
    value.seek(0)
    if header.startswith(b"PK\x03\x04"):
        return
    if header.startswith(b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1"):
        return
    try:
        header.decode("utf-8")
    except UnicodeDecodeError:
        raise serializers.ValidationError(
            "File does not appear to be a valid CSV, Excel, or JSON file."
        )


class DatasetSerializer(serializers.ModelSerializer):
    uploaded_by_email = serializers.CharField(source="uploaded_by.email", read_only=True)

    class Meta:
        model = Dataset
        fields = [
            "id", "name", "description", "file", "file_size",
            "row_count", "column_count", "status", "error_message", "analysis_results",
            "uploaded_by_email", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "file_size", "row_count", "column_count",
            "status", "error_message", "analysis_results", "uploaded_by_email",
            "created_at", "updated_at",
        ]

    def validate_file(self, value):
        from django.conf import settings
        max_size = settings.MAX_UPLOAD_SIZE
        allowed_types = [
            "text/csv",
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/json",
            "application/octet-stream",
        ]
        if value.size > max_size:
            raise serializers.ValidationError("File size must not exceed 10 MB.")
        if value.content_type not in allowed_types:
            raise serializers.ValidationError(
                "Unsupported file type. Use CSV, Excel, or JSON."
            )
        filename = _sanitize_filename(value.name)
        ext = os.path.splitext(filename)[1].lower()
        allowed_extensions = [".csv", ".xlsx", ".xls", ".json"]
        if ext not in allowed_extensions:
            raise serializers.ValidationError(
                f"Unsupported file extension '{ext}'. Allowed: {', '.join(allowed_extensions)}"
            )
        _validate_file_magic(value)
        value.name = filename
        return value

    def create(self, validated_data):
        file = validated_data["file"]
        validated_data["file_size"] = file.size
        validated_data["organization"] = self.context["request"].user.organization
        validated_data["uploaded_by"] = self.context["request"].user
        logger.info(
            "Dataset upload: user=%s org=%s filename=%s size=%s",
            self.context["request"].user.email,
            validated_data["organization"].id,
            file.name,
            file.size,
        )
        return super().create(validated_data)
