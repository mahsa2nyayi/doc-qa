from pathlib import Path

from django.conf import settings
from rest_framework import serializers

from pipeline.extract import SUPPORTED_EXTENSIONS

from .models import Document


class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = [
            "id",
            "title",
            "original_name",
            "status",
            "error",
            "page_count",
            "chunk_count",
            "created_at",
        ]
        read_only_fields = fields


class UploadSerializer(serializers.Serializer):
    file = serializers.FileField(help_text="PDF, TXT or MD.")
    title = serializers.CharField(max_length=200, required=False, allow_blank=True)

    def validate_file(self, uploaded):
        extension = Path(uploaded.name).suffix.lower()
        if extension not in SUPPORTED_EXTENSIONS:
            raise serializers.ValidationError(
                f"Unsupported file type. Use one of: {', '.join(SUPPORTED_EXTENSIONS)}."
            )
        limit = settings.MAX_UPLOAD_MB * 1024 * 1024
        if uploaded.size > limit:
            raise serializers.ValidationError(f"File is larger than {settings.MAX_UPLOAD_MB:g} MB.")
        if extension == ".pdf":
            header = uploaded.read(5)
            uploaded.seek(0)
            if header != b"%PDF-":
                raise serializers.ValidationError("The file is not a valid PDF.")
        return uploaded
