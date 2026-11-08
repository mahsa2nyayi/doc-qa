"""Vector search over a user's indexed chunks."""
from dataclasses import dataclass

from django.conf import settings
from pgvector.django import CosineDistance

from apps.documents.models import Chunk, DocumentStatus
from pipeline.embed import get_embedder


@dataclass(frozen=True)
class Hit:
    chunk: Chunk
    score: float  # cosine similarity, 1.0 = identical direction


def search(*, user, query: str, top_k: int = 5, document_ids: list[int] | None = None) -> list[Hit]:
    """Best chunks for ``query`` among the user's own, fully indexed documents."""
    query_vector = get_embedder().embed_query(query)

    chunks = Chunk.objects.filter(document__owner=user, document__status=DocumentStatus.READY)
    if document_ids:
        chunks = chunks.filter(document_id__in=document_ids)

    rows = (
        chunks.select_related("document")
        .annotate(distance=CosineDistance("embedding", query_vector))
        .order_by("distance")[:top_k]
    )
    hits = [Hit(chunk=row, score=1.0 - row.distance) for row in rows]
    return [hit for hit in hits if hit.score >= settings.RETRIEVAL_MIN_SCORE]
