"""
Text & PDF Ingestion module using PyMuPDF (fitz).
Extracts and sanitizes text from pasted strings or PDF files with chunking support.
"""

import re
from pathlib import Path
from typing import Union, List
try:
    import pymupdf as fitz
except ImportError:
    import fitz
from src.schemas import BaseModel
from core.logger import setup_logger

logger = setup_logger("ingest")


class IngestResult(BaseModel):
    source_type: str  # "text" or "pdf"
    file_name: str
    raw_char_count: int
    cleaned_char_count: int
    clean_text: str
    chunks: List[str]


class TextIngestor:
    """Extracts, cleans, and chunks input text or PDF files."""

    MAX_CHUNK_CHARS = 4000
    CHUNK_OVERLAP_CHARS = 200

    @classmethod
    def clean_text(cls, text: str) -> str:
        """Sanitizes raw text, collapses whitespace, and removes noisy artifacts."""
        if not text:
            return ""

        # Normalize line breaks
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # Remove page numbers and common header/footer artifact patterns
        text = re.sub(r"(?i)\bpage\s+\d+(\s+of\s+\d+)?\b", "", text)
        text = re.sub(r"^\s*\d+\s*$", "", text, flags=re.MULTILINE)

        # Remove non-printable control characters while preserving standard punctuation
        text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", text)

        # Strip line-trailing/leading spaces and collapse excessive blank lines
        text = re.sub(r"[ \t]+\n", "\n", text)
        text = re.sub(r"\n[ \t]+", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)

        # Collapse multi-spaces
        text = re.sub(r"[ \t]{2,}", " ", text)

        return text.strip()

    @classmethod
    def chunk_text(cls, text: str, max_chunk_size: int = MAX_CHUNK_CHARS, overlap: int = CHUNK_OVERLAP_CHARS) -> List[str]:
        """Splits long text into coherent paragraphs without cutting sentences."""
        if len(text) <= max_chunk_size:
            return [text]

        paragraphs = text.split("\n\n")
        chunks: List[str] = []
        current_chunk = ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            if len(current_chunk) + len(para) + 2 <= max_chunk_size:
                current_chunk = f"{current_chunk}\n\n{para}" if current_chunk else para
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = para

        if current_chunk:
            chunks.append(current_chunk)

        logger.info(f"Chunked input ({len(text)} chars) into {len(chunks)} sections.")
        return chunks

    @classmethod
    def from_text(cls, text: str, title: str = "Direct Input") -> IngestResult:
        """Ingests raw pasted text."""
        logger.info(f"Ingesting raw text (title: '{title}', raw length: {len(text)})")
        clean = cls.clean_text(text)
        chunks = cls.chunk_text(clean)
        return IngestResult(
            source_type="text",
            file_name=title,
            raw_char_count=len(text),
            cleaned_char_count=len(clean),
            clean_text=clean,
            chunks=chunks,
        )

    @classmethod
    def from_pdf(cls, file_path_or_bytes: Union[str, Path, bytes], file_name: str = "document.pdf") -> IngestResult:
        """Extracts text from a PDF file using PyMuPDF (fitz)."""
        logger.info(f"Extracting text from PDF: {file_name}")
        raw_text_parts: List[str] = []

        try:
            if isinstance(file_path_or_bytes, (str, Path)):
                doc = fitz.open(str(file_path_or_bytes))
            else:
                doc = fitz.open(stream=file_path_or_bytes, filetype="pdf")

            total_pages = len(doc)
            for page_num in range(total_pages):
                page = doc[page_num]
                page_text = page.get_text("text")
                if page_text:
                    raw_text_parts.append(page_text)

            doc.close()
            full_raw = "\n\n".join(raw_text_parts)
            logger.info(f"Extracted {len(full_raw)} characters from {total_pages} PDF pages.")

            clean = cls.clean_text(full_raw)
            chunks = cls.chunk_text(clean)

            return IngestResult(
                source_type="pdf",
                file_name=file_name,
                raw_char_count=len(full_raw),
                cleaned_char_count=len(clean),
                clean_text=clean,
                chunks=chunks,
            )

        except Exception as e:
            logger.error(f"Failed to read PDF '{file_name}': {str(e)}", exc_info=True)
            raise ValueError(f"Could not extract text from PDF: {str(e)}") from e
