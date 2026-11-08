"""Turn an uploaded file into a list of pages of clean text."""
import io
import re
from dataclasses import dataclass

from pypdf import PdfReader

SUPPORTED_EXTENSIONS = (".pdf", ".txt", ".md")
TEXT_PAGE_CHARS = 3000


class ExtractionError(Exception):
    """The file could not be turned into text. The message is safe to show to users."""


@dataclass(frozen=True)
class Page:
    number: int  # 1-based
    text: str


def extract_pages(data: bytes, filename: str) -> list[Page]:
    name = filename.lower()
    if name.endswith(".pdf"):
        pages = _from_pdf(data)
    elif name.endswith((".txt", ".md")):
        pages = _from_text(data)
    else:
        raise ExtractionError("Unsupported file type. Use PDF, TXT or MD.")
    if not pages:
        raise ExtractionError(
            "No text could be extracted. Scanned PDFs need OCR, which is not supported."
        )
    return pages


def _from_pdf(data: bytes) -> list[Page]:
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            raise ExtractionError("Encrypted PDFs are not supported.")
        pages = []
        for number, page in enumerate(reader.pages, start=1):
            text = _normalize(page.extract_text() or "")
            if text:
                pages.append(Page(number, text))
        return pages
    except ExtractionError:
        raise
    except Exception as exc:  # pypdf raises many different types on broken files
        raise ExtractionError("The PDF is damaged or could not be read.") from exc


def _from_text(data: bytes) -> list[Page]:
    text = data.decode("utf-8", errors="replace")
    blocks = text.split("\f") if "\f" in text else _split_long_text(text)
    pages = []
    for number, block in enumerate(blocks, start=1):
        cleaned = _normalize(block)
        if cleaned:
            pages.append(Page(number, cleaned))
    return pages


def _split_long_text(text: str) -> list[str]:
    """Group paragraphs into pseudo-pages so long text files still get locations."""
    blocks, current = [], ""
    for paragraph in re.split(r"\n\s*\n", text):
        if current and len(current) + len(paragraph) > TEXT_PAGE_CHARS:
            blocks.append(current)
            current = ""
        current += paragraph + "\n\n"
    if current.strip():
        blocks.append(current)
    return blocks


def _normalize(text: str) -> str:
    text = text.replace("\r", "").replace("\x00", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)  # PDF line wraps inside a paragraph
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
