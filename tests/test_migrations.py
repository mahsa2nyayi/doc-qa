import pytest
from django.core.management import call_command


@pytest.mark.django_db
def test_models_and_migrations_are_in_sync():
    try:
        call_command("makemigrations", check=True, dry_run=True, verbosity=0)
    except SystemExit:
        pytest.fail(
            "Model changes are not reflected in the migrations. "
            "Run `python manage.py makemigrations` and commit the result."
        )


@pytest.mark.django_db
def test_pgvector_extension_and_index_exist():
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
        assert cursor.fetchone() is not None
        cursor.execute("SELECT indexdef FROM pg_indexes WHERE indexname = 'chunk_embedding_hnsw'")
        definition = cursor.fetchone()[0]
    assert "hnsw" in definition and "vector_cosine_ops" in definition
