from pathlib import Path

from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from . import services
from .models import Document
from .serializers import DocumentSerializer, UploadSerializer


class DocumentViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Your documents. Users only ever see their own."""

    serializer_class = DocumentSerializer
    parser_classes = [MultiPartParser, FormParser]
    throttle_scope = "upload"

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):  # schema generation
            return Document.objects.none()
        return Document.objects.filter(owner=self.request.user)

    def get_throttles(self):
        # Only uploads are rate limited; reads and deletes are cheap.
        return [ScopedRateThrottle()] if self.action == "create" else []

    @extend_schema(
        request={"multipart/form-data": UploadSerializer},
        responses={202: DocumentSerializer},
    )
    def create(self, request):
        """Upload a document. Processing runs in the background: poll the document
        until its status is `ready` (or `failed`, with the reason in `error`)."""
        serializer = UploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        uploaded = serializer.validated_data["file"]
        title = serializer.validated_data.get("title") or Path(uploaded.name).stem

        document = Document.objects.create(
            owner=request.user,
            title=title[:200],
            file=uploaded,
            original_name=uploaded.name[:255],
        )
        services.enqueue_processing(document)
        return Response(DocumentSerializer(document).data, status=status.HTTP_202_ACCEPTED)

    def perform_destroy(self, instance):
        instance.file.delete(save=False)
        instance.delete()  # chunks are removed by the cascade
