import django.db.models.deletion
import pgvector.django
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        pgvector.django.VectorExtension(),
        migrations.CreateModel(
            name="Document",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("title", models.CharField(max_length=200)),
                ("file", models.FileField(upload_to="documents/%Y/%m/")),
                ("original_name", models.CharField(max_length=255)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("processing", "Processing"),
                            ("ready", "Ready"),
                            ("failed", "Failed"),
                        ],
                        default="pending",
                        max_length=12,
                    ),
                ),
                ("error", models.TextField(blank=True)),
                ("page_count", models.PositiveIntegerField(default=0)),
                ("chunk_count", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "owner",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="documents",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="Chunk",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("index", models.PositiveIntegerField()),
                ("page", models.PositiveIntegerField()),
                ("text", models.TextField()),
                ("embedding", pgvector.django.VectorField(dimensions=384)),
                (
                    "document",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="chunks",
                        to="documents.document",
                    ),
                ),
            ],
            options={
                "ordering": ["document_id", "index"],
            },
        ),
        migrations.AddConstraint(
            model_name="chunk",
            constraint=models.UniqueConstraint(
                fields=("document", "index"), name="uniq_chunk_index_per_document"
            ),
        ),
        migrations.AddIndex(
            model_name="chunk",
            index=pgvector.django.HnswIndex(
                fields=["embedding"],
                m=16,
                ef_construction=64,
                name="chunk_embedding_hnsw",
                opclasses=["vector_cosine_ops"],
            ),
        ),
    ]
