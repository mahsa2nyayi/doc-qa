"""Fixtures for the database tests.

Django and DRF are imported inside the fixtures on purpose: the tests in
tests/pipeline need none of them and must run in a bare Python environment.
"""
import pytest

from tests.helpers import ALL_SAMPLES, sample_bytes


def _uses_database(request) -> bool:
    return "db" in request.fixturenames or request.node.get_closest_marker("django_db") is not None


@pytest.fixture(autouse=True)
def _isolate_media(request, tmp_path):
    """Uploaded files go to a temporary folder, never into the repository."""
    if _uses_database(request):
        request.getfixturevalue("settings").MEDIA_ROOT = tmp_path


@pytest.fixture(autouse=True)
def _no_score_threshold(request):
    """Tests about ranking and result counts must not depend on the score cut-off;
    the cut-off itself is tested explicitly in test_retrieval.py."""
    if _uses_database(request):
        request.getfixturevalue("settings").RETRIEVAL_MIN_SCORE = 0.0


@pytest.fixture(autouse=True)
def _clear_throttle_cache(request):
    if _uses_database(request):
        from django.core.cache import cache

        cache.clear()


@pytest.fixture
def user(db):
    from django.contrib.auth import get_user_model

    return get_user_model().objects.create_user(username="alice", password="pw-alice-12345")


@pytest.fixture
def other_user(db):
    from django.contrib.auth import get_user_model

    return get_user_model().objects.create_user(username="bob", password="pw-bob-12345")


@pytest.fixture
def client_for():
    from rest_framework.test import APIClient

    def _make(user):
        client = APIClient()
        client.force_authenticate(user)
        return client

    return _make


@pytest.fixture
def upload(monkeypatch, django_capture_on_commit_callbacks):
    """Upload through the API and run the background job inline.

    In production the work happens in a Celery worker; here ``.delay`` is
    replaced by a direct call so tests do not need Redis.
    """
    from django.core.files.uploadedfile import SimpleUploadedFile

    from apps.documents import services, tasks

    monkeypatch.setattr(
        tasks.process_document, "delay", lambda document_id: services.process_document(document_id)
    )

    def _upload(client, name=ALL_SAMPLES[0], data=None, **extra):
        payload = data if data is not None else sample_bytes(name)
        with django_capture_on_commit_callbacks(execute=True):
            return client.post(
                "/api/documents/",
                {"file": SimpleUploadedFile(name, payload), **extra},
                format="multipart",
            )

    return _upload


@pytest.fixture
def indexed(user, client_for, upload):
    """The three sample documents, uploaded and indexed for ``user``."""
    client = client_for(user)
    for name in ALL_SAMPLES:
        assert upload(client, name).status_code == 202
    return user
