from celery import shared_task

from . import services


@shared_task(name="documents.process_document")
def process_document(document_id: int) -> None:
    services.process_document(document_id)
