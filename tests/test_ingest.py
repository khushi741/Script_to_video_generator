import pytest
from src.ingest import TextIngestor, IngestResult


def test_clean_text_basic():
    dirty = "  This is a   sentence. \r\n\r\n\r\n\r\nWith  extra   spaces.  "
    cleaned = TextIngestor.clean_text(dirty)
    assert cleaned == "This is a sentence.\n\nWith extra spaces."


def test_clean_text_page_numbers():
    raw = "Introduction to Cells\nPage 4 of 20\n\nCells are the basic unit of life.\n12\nNext line."
    cleaned = TextIngestor.clean_text(raw)
    assert "Page 4 of 20" not in cleaned
    assert "Cells are the basic unit of life." in cleaned


def test_chunk_text_short():
    short_text = "Short text under max chunk size."
    chunks = TextIngestor.chunk_text(short_text, max_chunk_size=100)
    assert len(chunks) == 1
    assert chunks[0] == short_text


def test_chunk_text_multi_paragraph():
    paragraphs = [f"Paragraph number {i} containing some explanatory text." for i in range(10)]
    full_text = "\n\n".join(paragraphs)
    chunks = TextIngestor.chunk_text(full_text, max_chunk_size=120)
    assert len(chunks) > 1
    # Verify all content is captured
    for p in paragraphs:
        assert any(p in c for c in chunks)


def test_from_text():
    sample = "Thermodynamics is the branch of physics dealing with heat and temperature."
    result = TextIngestor.from_text(sample, title="Physics Chapter 1")
    assert isinstance(result, IngestResult)
    assert result.source_type == "text"
    assert result.file_name == "Physics Chapter 1"
    assert result.clean_text == sample
    assert len(result.chunks) == 1
