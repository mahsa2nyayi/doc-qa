"""Document processing: file -> pages -> chunks -> embeddings -> database."""
import logging

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from pipeline.chunk import chunk_pages
from pipeline.embed import get_embedder
from pipeline.extract import ExtractionError, extract_pages

from .models import Chunk, Document, DocumentStatus

logger = logging.getLogger(__name__)

GENERIC_FAILURE = "Processing failed. Try again or upload a different file."


def enqueue_processing(document: Document) -> None:
    """Queue processing once the surrounding transaction has committed, so the
    worker never looks for a row that is not visible yet."""
    from .tasks import process_document  # imported here to avoid a circular import

    transaction.on_commit(lambda: process_document.delay(document.id))


def process_document(document_id: int) -> None:
    """Index one document. Safe to call twice: a finished document is left alone."""
    try:
        document = Document.objects.get(pk=document_id)
    except Document.DoesNotExist:
        return
    if document.status == DocumentStatus.READY:
        return

    _set_status(document.pk, DocumentStatus.PROCESSING)
    try:
        with document.file.open("rb") as handle:
            data = handle.read()
        pages = extract_pages(data, document.original_name)
        chunks = chunk_pages(pages, settings.CHUNK_MAX_CHARS, settings.CHUNK_OVERLAP_CHARS)
        vectors = get_embedder().embed_documents([chunk.text for chunk in chunks])

        with transaction.atomic():
            document.chunks.all().delete()
            Chunk.objects.bulk_create(
                [
                    Chunk(
                        document=document,
                        index=chunk.index,
                        page=chunk.page,
                        text=chunk.text,
                        embedding=vector,
                    )
                    for chunk, vector in zip(chunks, vectors, strict=True)
                ],
                batch_size=200,
            )
            _set_status(
                document.pk,
                DocumentStatus.READY,
                page_count=len(pages),
                chunk_count=len(chunks),
            )
    except ExtractionError as exc:
        _set_status(document.pk, DocumentStatus.FAILED, error=str(exc))
    except Exception:
        logger.exception("Processing document %s failed", document.pk)
        _set_status(document.pk, DocumentStatus.FAILED, error=GENERIC_FAILURE)


def _set_status(document_id: int, status: DocumentStatus, error: str = "", **fields) -> None:
    Document.objects.filter(pk=document_id).update(
        status=status.value, error=error, updated_at=timezone.now(), **fields
    )
