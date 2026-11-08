import pytest

from pipeline.chunk import chunk_pages, split_sentences
from pipeline.extract import Page, extract_pages
from tests.helpers import ALL_SAMPLES, sample_bytes


def numbered_sentences(count: int, start: int = 0) -> str:
    return " ".join(f"Sentence number {i} is here." for i in range(start, start + count))


@pytest.mark.parametrize("max_chars,overlap", [(100, 20), (250, 50), (400, 80), (800, 150)])
@pytest.mark.parametrize("name", ALL_SAMPLES)
def test_no_chunk_exceeds_the_limit(name, max_chars, overlap):
    chunks = chunk_pages(extract_pages(sample_bytes(name), name), max_chars, overlap)
    assert chunks
    assert all(0 < len(chunk.text) <= max_chars for chunk in chunks)


def test_indices_are_sequential_across_pages():
    pages = [Page(1, numbered_sentences(20)), Page(2, numbered_sentences(20, start=100))]
    chunks = chunk_pages(pages, max_chars=150, overlap_chars=30)
    assert [chunk.index for chunk in chunks] == list(range(len(chunks)))


def test_chunks_never_cross_a_page_boundary():
    pages = [Page(1, numbered_sentences(15)), Page(2, numbered_sentences(15, start=500))]
    for chunk in chunk_pages(pages, max_chars=150, overlap_chars=30):
        numbers = {int(word) for word in chunk.text.split() if word.isdigit()}
        assert all(n < 500 for n in numbers) if chunk.page == 1 else all(n >= 500 for n in numbers)


def test_consecutive_chunks_overlap():
    chunks = chunk_pages([Page(1, numbered_sentences(30))], max_chars=200, overlap_chars=60)
    assert len(chunks) > 2
    for before, after in zip(chunks, chunks[1:], strict=False):
        last_sentence = split_sentences(before.text)[-1]
        assert last_sentence in after.text


def test_without_overlap_chunks_do_not_repeat_text():
    chunks = chunk_pages([Page(1, numbered_sentences(30))], max_chars=200, overlap_chars=0)
    seen = [s for chunk in chunks for s in split_sentences(chunk.text)]
    assert len(seen) == len(set(seen)) == 30


def test_no_sentence_is_lost():
    text = numbered_sentences(40)
    chunks = chunk_pages([Page(1, text)], max_chars=180, overlap_chars=40)
    joined = " ".join(chunk.text for chunk in chunks)
    assert all(sentence in joined for sentence in split_sentences(text))


def test_a_sentence_longer_than_a_chunk_is_split_on_words():
    long_sentence = " ".join(f"word{i}" for i in range(300)) + "."
    chunks = chunk_pages([Page(1, long_sentence)], max_chars=120, overlap_chars=0)
    assert len(chunks) > 5
    assert all(len(chunk.text) <= 120 for chunk in chunks)


def test_a_single_huge_token_is_hard_split():
    chunks = chunk_pages([Page(1, "x" * 1000)], max_chars=100, overlap_chars=0)
    assert [len(chunk.text) for chunk in chunks] == [100] * 10


def test_short_page_becomes_one_chunk():
    chunks = chunk_pages([Page(3, "Just one short sentence.")])
    assert [(c.index, c.page, c.text) for c in chunks] == [(0, 3, "Just one short sentence.")]


def test_no_pages_no_chunks():
    assert chunk_pages([]) == []


@pytest.mark.parametrize("max_chars,overlap", [(10, 0), (200, 200), (200, -1)])
def test_invalid_parameters(max_chars, overlap):
    with pytest.raises(ValueError):
        chunk_pages([Page(1, "text")], max_chars, overlap)
