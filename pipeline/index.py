"""A tiny in-memory vector index.

Used by the evaluation script and tests. In the web app the same job is done
by PostgreSQL with pgvector (see apps/retrieval).
"""
from dataclasses import dataclass


def dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))


@dataclass(frozen=True)
class IndexedChunk:
    document: str
    page: int
    index: int
    text: str
    vector: list[float]


class InMemoryIndex:
    def __init__(self) -> None:
        self.items: list[IndexedChunk] = []

    def add(self, document: str, page: int, index: int, text: str, vector: list[float]) -> None:
        self.items.append(IndexedChunk(document, page, index, text, vector))

    def search(self, query_vector: list[float], k: int = 5) -> list[tuple[float, IndexedChunk]]:
        """Best ``k`` chunks by cosine similarity (vectors are already normalised)."""
        scored = [(dot(query_vector, item.vector), item) for item in self.items]
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return scored[:k]
