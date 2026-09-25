"""Pluggable document ingestion layer — PDF, DOCX, plain text."""
from __future__ import annotations

from pathlib import Path
from typing import Optional


def extract_text(file_path: str) -> str:
    """Extract plain text from a file, dispatching by extension."""
    path = Path(file_path)
    ext = path.suffix.lower()

    if ext == ".pdf":
        return _extract_pdf(path)
    elif ext in (".docx", ".doc"):
        return _extract_docx(path)
    else:
        # Default: read as plain text
        try:
            return path.read_text(errors="replace")
        except Exception as e:
            return f"[Could not read file: {e}]"


def _extract_pdf(path: Path) -> str:
    try:
        import PyPDF2

        reader = PyPDF2.PdfReader(str(path))
        pages = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
        return "\n\n".join(pages)
    except ImportError:
        return "[PyPDF2 not installed — PDF text extraction unavailable]"
    except Exception as e:
        return f"[PDF extraction error: {e}]"


def _extract_docx(path: Path) -> str:
    try:
        from docx import Document

        doc = Document(str(path))
        return "\n".join(para.text for para in doc.paragraphs if para.text.strip())
    except ImportError:
        return "[python-docx not installed — DOCX text extraction unavailable]"
    except Exception as e:
        return f"[DOCX extraction error: {e}]"
