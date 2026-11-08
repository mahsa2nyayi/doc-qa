"""Split page text into overlapping, sentence-aligned chunks.

Chunks never cross a page boundary, so every chunk has an exact page number
that can be shown as a citation.
"""
import re
from collections.abc import Iterator
from dataclasses import dataclass

from .extract import Page

DEFAULT_MAX_CHARS = 400
DEFAULT_OVERLAP_CHARS = 80

_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?؟])\s+|\n{2,}")


@dataclass(frozen=True)
class Chunk:
    index: int  # position within the document, 0-based
    page: int
    text: str


def split_sentences(text: str) -> list[str]:
    return [part.strip() for part in _SENTENCE_BOUNDARY.split(text) if part and part.strip()]


def chunk_pages(
    pages: list[Page],
    max_chars: int = DEFAULT_MAX_CHARS,
    overlap_chars: int = DEFAULT_OVERLAP_CHARS,
) -> list[Chunk]:
    if max_chars < 50:
        raise ValueError("max_chars must be at least 50")
    if not 0 <= overlap_chars < max_chars:
        raise ValueError("overlap_chars must be >= 0 and smaller than max_chars")

    chunks: list[Chunk] = []
    for page in pages:
        for text in _chunk_page(page.text, max_chars, overlap_chars):
            chunks.append(Chunk(index=len(chunks), page=page.number, text=text))
    return chunks


def _chunk_page(text: str, max_chars: int, overlap_chars: int) -> list[str]:
    sentences = [piece for s in split_sentences(text) for piece in _fit(s, max_chars)]
    out: list[str] = []
    current: list[str] = []
    fresh = False  # does `current` hold anything not yet emitted?

    for sentence in sentences:
        if current and _joined_len(current) + 1 + len(sentence) > max_chars:
            if fresh:
                out.append(" ".join(current))
            tail = _tail(current, overlap_chars)
            current = tail if _joined_len(tail) + 1 + len(sentence) <= max_chars else []
            fresh = False
        current.append(sentence)
        fresh = True

    if current and fresh:
        out.append(" ".join(current))
    return out


def _joined_len(items: list[str]) -> int:
    return sum(len(item) for item in items) + max(len(items) - 1, 0)


def _tail(sentences: list[str], overlap_chars: int) -> list[str]:
    """Trailing sentences that fit into the overlap budget."""
    tail: list[str] = []
    for sentence in reversed(sentences):
        if _joined_len([sentence, *tail]) > overlap_chars:
            break
        tail.insert(0, sentence)
    return tail


def _fit(sentence: str, max_chars: int) -> Iterator[str]:
    """Break a sentence that is longer than a chunk into word-aligned pieces."""
    if len(sentence) <= max_chars:
        yield sentence
        return
    current = ""
    for word in sentence.split():
        if len(word) > max_chars:  # one enormous token, e.g. a base64 blob
            if current:
                yield current
                current = ""
            for start in range(0, len(word), max_chars):
                yield word[start : start + max_chars]
            continue
        candidate = f"{current} {word}".strip()
        if len(candidate) > max_chars:
            yield current
            current = word
        else:
            current = candidate
    if current:
        yield current
