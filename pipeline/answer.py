"""Extractive answering: pick the sentences of a passage that best match a question."""
from .chunk import split_sentences
from .embed import Embedder
from .index import dot


def best_sentences(embedder: Embedder, question: str, text: str, n: int = 2) -> str:
    """Return the ``n`` sentences of ``text`` closest to ``question``, in original order."""
    sentences = split_sentences(text)
    if len(sentences) <= n:
        return " ".join(sentences)
    query = embedder.embed_query(question)
    vectors = embedder.embed_documents(sentences)
    ranked = sorted(range(len(sentences)), key=lambda i: dot(query, vectors[i]), reverse=True)[:n]
    return " ".join(sentences[i] for i in sorted(ranked))
