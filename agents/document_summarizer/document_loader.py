"""
document_loader.py
===================
Extracts plain text from a handful of common document formats so the
summarizer doesn't care what format the input arrived in. Kept
dependency-light: only pulls in pypdf / python-docx when actually asked
to read that format.
"""

from pathlib import Path


def load_text(file_path: str) -> str:
    """Reads `file_path` and returns its plain-text contents, dispatching
    on file extension. Raises ValueError for unsupported formats."""
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix in (".txt", ".md"):
        return path.read_text(encoding="utf-8")

    if suffix == ".pdf":
        return _load_pdf(path)

    if suffix == ".docx":
        return _load_docx(path)

    raise ValueError(
        f"Unsupported file type '{suffix}'. Supported: .txt, .md, .pdf, .docx"
    )


def _load_pdf(path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    pages_text = [page.extract_text() or "" for page in reader.pages]
    return "\n\n".join(pages_text)


def _load_docx(path: Path) -> str:
    import docx

    doc = docx.Document(str(path))
    return "\n".join(p.text for p in doc.paragraphs)
