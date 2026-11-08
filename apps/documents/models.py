from django.conf import settings
from django.db import models
from pgvector.django import HnswIndex, VectorField

from pipeline.embed import EMBEDDING_DIM


class DocumentStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    PROCESSING = "processing", "Processing"
    READY = "ready", "Ready"
    FAILED = "failed", "Failed"


class Document(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="documents"
    )
    title = models.CharField(max_length=200)
    file = models.FileField(upload_to="documents/%Y/%m/")
    original_name = models.CharField(max_length=255)
    status = models.CharField(
        max_length=12, choices=DocumentStatus.choices, default=DocumentStatus.PENDING.value
    )
    error = models.TextField(blank=True)
    page_count = models.PositiveIntegerField(default=0)
    chunk_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title


class Chunk(models.Model):
    """A passage of a document with its embedding. ``page`` is the citation."""

    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="chunks")
    index = models.PositiveIntegerField()
    page = models.PositiveIntegerField()
    text = models.TextField()
    embedding = VectorField(dimensions=EMBEDDING_DIM)

    class Meta:
        ordering = ["document_id", "index"]
        constraints = [
            models.UniqueConstraint(
                fields=["document", "index"], name="uniq_chunk_index_per_document"
            ),
        ]
        indexes = [
            # Approximate nearest-neighbour index for cosine distance.
            HnswIndex(
                name="chunk_embedding_hnsw",
                fields=["embedding"],
                m=16,
                ef_construction=64,
                opclasses=["vector_cosine_ops"],
            ),
        ]

    def __str__(self) -> str:
        return f"{self.document_id}#{self.index} (p.{self.page})"
