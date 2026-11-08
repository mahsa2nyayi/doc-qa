from pathlib import Path

DOCS_DIR = Path(__file__).resolve().parent.parent / "eval" / "docs"
HANDBOOK = "nordlicht_handbook.pdf"
MANUAL = "aurora7_manual.pdf"
GUIDE = "fernwood_contributing.pdf"
ALL_SAMPLES = (HANDBOOK, MANUAL, GUIDE)


def sample_bytes(name: str) -> bytes:
    return (DOCS_DIR / name).read_bytes()
