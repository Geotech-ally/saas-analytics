import os
import logging
from rest_framework import serializers
from .models import Dataset

logger = logging.getLogger(__name__)


class DatasetSerializer(serializers.ModelSerializer):
    uploaded_by_email = serializers.CharField(source="uploaded_by.email", read_only=True)

    class Meta:
        model = Dataset
        fields = [
            "id", "name", "description", "file", "file_size",
            "row_count", "column_count", "status", "error_message",
            "uploaded_by_email", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "file_size", "row_count", "column_count",
            "status", "error_message", "uploaded_by_email",
            "created_at", "updated_at",
        ]

    def validate_file(self, value):
        max_size = 10 * 1024 * 1024  # 10 MB
        allowed_types = [
            "text/csv",
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ]
        if value.size > max_size:
            raise serializers.ValidationError("File size must not exceed 10 MB.")
        if value.content_type not in allowed_types:
            raise serializers.ValidationError(
                "Unsupported file type. Use CSV or Excel (.csv, .xlsx, .xls)."
            )
        filename = value.name
        if ".." in filename or "/" in filename:
            raise serializers.ValidationError("Invalid file name. Path traversal is not allowed.")
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
