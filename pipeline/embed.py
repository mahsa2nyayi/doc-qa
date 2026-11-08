"""Text embeddings behind one small interface.

Backends (selected with the EMBEDDING_BACKEND environment variable):

* ``hash`` (default): feature hashing of word unigrams and bigrams. Needs no
  model download and no API key and is fully deterministic, so the repository
  runs and tests anywhere. It matches words, not meaning.
* ``sentence-transformers``: a real multilingual model
  (``intfloat/multilingual-e5-small``, 384 dimensions by default). Install with
  ``pip install -r requirements-ml.txt``.

Both return L2-normalised vectors of EMBEDDING_DIM numbers, so cosine
similarity is a plain dot product and both fit the same database column.
"""
import hashlib
import math
import os
import re
from collections import Counter
from functools import lru_cache
from typing import Protocol

EMBEDDING_DIM = 384

_TOKEN = re.compile(r"\w+", re.UNICODE)
_STOPWORDS = frozenset(
    """a an the and or of to in on at for is are be by it its as with that this from can do does
    how what when where which who why i my me you your we our should must will not no than then if
    up so per have has had been was were after once about many much long often there their""".split()
)


class Embedder(Protocol):
    dim: int

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class HashingEmbedder:
    def __init__(self, dim: int = EMBEDDING_DIM):
        self.dim = dim

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    def _embed(self, text: str) -> list[float]:
        counts = Counter(_features(text))
        vector = [0.0] * self.dim
        for feature, count in counts.items():
            digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
            number = int.from_bytes(digest, "big")
            sign = 1.0 if (number >> 63) & 1 else -1.0
            vector[number % self.dim] += sign * (1.0 + math.log(count))
        return _normalize(vector)


class SentenceTransformerEmbedder:
    def __init__(self, model_name: str | None = None):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(
                "EMBEDDING_BACKEND=sentence-transformers needs the optional "
                "dependencies: pip install -r requirements-ml.txt"
            ) from exc
        self.model_name = model_name or os.environ.get(
            "EMBEDDING_MODEL", "intfloat/multilingual-e5-small"
        )
        self._model = SentenceTransformer(self.model_name)
        self.dim = self._model.get_sentence_embedding_dimension()
        if self.dim != EMBEDDING_DIM:
            raise RuntimeError(
                f"Model {self.model_name} produces {self.dim} dimensions but the database "
                f"column has {EMBEDDING_DIM}. Pick a {EMBEDDING_DIM}-dimension model or "
                "change EMBEDDING_DIM and add a migration."
            )
        # E5 models are trained with these prefixes; other models do not use them.
        self._is_e5 = "e5" in self.model_name.lower()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        prefix = "passage: " if self._is_e5 else ""
        return self._encode([prefix + t for t in texts])

    def embed_query(self, text: str) -> list[float]:
        prefix = "query: " if self._is_e5 else ""
        return self._encode([prefix + text])[0]

    def _encode(self, texts: list[str]) -> list[list[float]]:
        return self._model.encode(texts, normalize_embeddings=True).tolist()


@lru_cache(maxsize=4)
def get_embedder(backend: str | None = None) -> Embedder:
    backend = (backend or os.environ.get("EMBEDDING_BACKEND", "hash")).lower()
    if backend == "hash":
        return HashingEmbedder()
    if backend in ("sentence-transformers", "st"):
        return SentenceTransformerEmbedder()
    raise ValueError(f"Unknown EMBEDDING_BACKEND: {backend!r}")


def _features(text: str) -> list[str]:
    tokens = [
        _stem(token)
        for token in _TOKEN.findall(text.lower())
        if token not in _STOPWORDS and len(token) > 1
    ]
    return tokens + [f"{a}_{b}" for a, b in zip(tokens, tokens[1:], strict=False)]  # pairs


def _stem(token: str) -> str:
    """Very crude suffix stripping so 'devices' and 'device' share a feature."""
    if len(token) > 4 and token.endswith("ies"):
        return token[:-3] + "y"
    if len(token) > 3 and token.endswith("s") and not token.endswith(("ss", "us", "is")):
        token = token[:-1]
    for suffix in ("ing", "ed"):
        if len(token) > len(suffix) + 3 and token.endswith(suffix):
            return token[: -len(suffix)]
    return token


def _normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in vector))
    return vector if norm == 0 else [x / norm for x in vector]
