import os

import pytest
from rest_framework.test import APIClient

from apps.documents.models import Chunk, Document, DocumentStatus
from apps.documents.services import process_document
from tests.helpers import HANDBOOK

pytestmark = pytest.mark.django_db


def test_register_and_get_token():
    client = APIClient()
    password = "Tr1cky-passphrase-77"
    created = client.post(
        "/api/auth/register/", {"username": "carol", "password": password}, format="json"
    )
    assert created.status_code == 201
    assert "password" not in created.data

    token = client.post(
        "/api/auth/token/", {"username": "carol", "password": password}, format="json"
    )
    assert token.status_code == 200

    client.credentials(HTTP_AUTHORIZATION=f"Token {token.data['token']}")
    assert client.get("/api/documents/").status_code == 200


def test_weak_password_is_rejected():
    response = APIClient().post(
        "/api/auth/register/", {"username": "dave", "password": "12345678"}, format="json"
    )
    assert response.status_code == 400


def test_endpoints_require_authentication():
    client = APIClient()
    assert client.get("/api/documents/").status_code == 401
    assert client.post("/api/ask/", {"question": "hi"}, format="json").status_code == 401


def test_upload_is_accepted_and_indexed(user, client_for, upload):
    client = client_for(user)
    response = upload(client, HANDBOOK)

    assert response.status_code == 202
    assert response.data["status"] == "pending"  # the response is sent before processing

    detail = client.get(f"/api/documents/{response.data['id']}/")
    assert detail.data["status"] == "ready"
    assert detail.data["page_count"] == 3
    assert detail.data["chunk_count"] == Chunk.objects.filter(document_id=response.data["id"]).count()
    assert detail.data["chunk_count"] > 3
    assert detail.data["title"] == "nordlicht_handbook"


def test_custom_title(user, client_for, upload):
    response = upload(client_for(user), HANDBOOK, title="Employee handbook")
    assert response.data["title"] == "Employee handbook"


def test_unsupported_extension_is_rejected(user, client_for, upload):
    response = upload(client_for(user), "malware.exe", data=b"MZ...")
    assert response.status_code == 400
    assert Document.objects.count() == 0


def test_fake_pdf_is_rejected(user, client_for, upload):
    response = upload(client_for(user), "report.pdf", data=b"this is plain text, not a pdf")
    assert response.status_code == 400
    assert Document.objects.count() == 0


def test_file_over_the_size_limit_is_rejected(user, client_for, upload, settings):
    settings.MAX_UPLOAD_MB = 0.001  # about 1 KB
    response = upload(client_for(user), "big.txt", data=b"word " * 1000)
    assert response.status_code == 400


def test_document_without_text_is_marked_failed(user, client_for, upload):
    client = client_for(user)
    response = upload(client, "blank.txt", data=b"   \n  \n ")
    assert response.status_code == 202

    detail = client.get(f"/api/documents/{response.data['id']}/")
    assert detail.data["status"] == "failed"
    assert "No text" in detail.data["error"]
    assert Chunk.objects.count() == 0


def test_processing_a_finished_document_again_changes_nothing(user, client_for, upload):
    response = upload(client_for(user), HANDBOOK)
    before = Chunk.objects.filter(document_id=response.data["id"]).count()

    process_document(response.data["id"])

    assert Chunk.objects.filter(document_id=response.data["id"]).count() == before
    assert Document.objects.get(pk=response.data["id"]).status == DocumentStatus.READY


def test_processing_a_missing_document_is_a_no_op():
    process_document(999_999)


def test_users_only_see_their_own_documents(user, other_user, client_for, upload):
    response = upload(client_for(user), HANDBOOK)
    document_id = response.data["id"]

    assert len(client_for(user).get("/api/documents/").data) == 1

    intruder = client_for(other_user)
    assert intruder.get("/api/documents/").data == []
    assert intruder.get(f"/api/documents/{document_id}/").status_code == 404
    assert intruder.delete(f"/api/documents/{document_id}/").status_code == 404
    assert Document.objects.filter(pk=document_id).exists()


def test_delete_removes_document_chunks_and_file(user, client_for, upload):
    client = client_for(user)
    response = upload(client, HANDBOOK)
    document = Document.objects.get(pk=response.data["id"])
    path = document.file.path
    assert Chunk.objects.filter(document=document).exists()

    assert client.delete(f"/api/documents/{document.id}/").status_code == 204

    assert not Document.objects.filter(pk=document.id).exists()
    assert not Chunk.objects.filter(document_id=document.id).exists()
    assert not os.path.exists(path)
