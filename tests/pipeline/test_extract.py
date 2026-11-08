import pytest

from pipeline.extract import ExtractionError, extract_pages
from tests.helpers import ALL_SAMPLES, MANUAL, sample_bytes


@pytest.mark.parametrize("name", ALL_SAMPLES)
def test_sample_pdfs_yield_three_numbered_pages(name):
    pages = extract_pages(sample_bytes(name), name)
    assert [page.number for page in pages] == [1, 2, 3]
    assert all(len(page.text) > 200 for page in pages)


def test_pdf_text_is_cleaned_and_on_the_right_page():
    pages = extract_pages(sample_bytes(MANUAL), MANUAL)
    assert "192.168.50.1" in pages[0].text
    assert "03:00" in pages[1].text
    assert "24 months" in pages[2].text
    assert "\n" not in pages[0].text  # line wraps inside a paragraph are joined


def test_plain_text_is_one_page():
    pages = extract_pages(b"Hello world.\n\nSecond paragraph.", "notes.txt")
    assert len(pages) == 1
    assert "Hello world." in pages[0].text and "Second paragraph." in pages[0].text


def test_long_text_is_split_into_numbered_pages():
    data = "\n\n".join(f"Paragraph {i}. " + "word " * 18 for i in range(200)).encode()
    pages = extract_pages(data, "long.md")
    assert len(pages) > 1
    assert [page.number for page in pages] == list(range(1, len(pages) + 1))


def test_form_feed_marks_page_breaks():
    pages = extract_pages(b"First page.\fSecond page.", "paged.txt")
    assert [page.text for page in pages] == ["First page.", "Second page."]


def test_unsupported_extension():
    with pytest.raises(ExtractionError, match="Unsupported"):
        extract_pages(b"data", "archive.zip")


def test_damaged_pdf():
    with pytest.raises(ExtractionError):
        extract_pages(b"%PDF-1.4 this is not really a pdf", "broken.pdf")


def test_whitespace_only_text_has_nothing_to_extract():
    with pytest.raises(ExtractionError, match="No text"):
        extract_pages(b"   \n\n \t ", "blank.txt")
