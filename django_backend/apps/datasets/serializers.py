from rest_framework import serializers
from .models import Dataset


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
        max_size = 50 * 1024 * 1024  # 50 MB
        allowed_types = ["text/csv", "application/json", "application/vnd.ms-excel",
                         "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"]
        if value.size > max_size:
            raise serializers.ValidationError("File size must not exceed 50 MB.")
        if value.content_type not in allowed_types:
            raise serializers.ValidationError(
                "Unsupported file type. Use CSV, JSON, or Excel."
            )
        return value

    def create(self, validated_data):
        file = validated_data["file"]
        validated_data["file_size"] = file.size
        validated_data["organization"] = self.context["request"].user.organization
        validated_data["uploaded_by"] = self.context["request"].user
        return super().create(validated_data)
