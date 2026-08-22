"""Tests for RAG text chunking (FR-09)."""

from app.rag.ingest import chunk_text


def test_short_text_is_single_chunk():
    chunks = chunk_text("hello world", chunk_size=800, overlap=100)
    assert chunks == ["hello world"]


def test_empty_text_yields_no_chunks():
    assert chunk_text("") == []


def test_respects_chunk_size():
    text = "a" * 2500
    chunks = chunk_text(text, chunk_size=800, overlap=100)
    assert all(len(c) <= 800 for c in chunks)


def test_chunks_overlap():
    """Overlap prevents a sentence split across a boundary from being lost."""
    text = "".join(str(i % 10) for i in range(2000))
    chunks = chunk_text(text, chunk_size=500, overlap=100)
    assert len(chunks) > 1
    # The tail of one chunk should reappear at the head of the next.
    assert chunks[0][-100:] == chunks[1][:100]


def test_covers_entire_text():
    """Reassembling the chunks must not drop any of the source characters."""
    text = "".join(str(i % 10) for i in range(3000))
    chunks = chunk_text(text, chunk_size=500, overlap=100)

    rebuilt = chunks[0]
    for chunk in chunks[1:]:
        rebuilt += chunk[100:]  # drop the overlapped prefix
    assert rebuilt == text


def test_no_empty_chunks():
    text = "b" * 1600
    chunks = chunk_text(text, chunk_size=400, overlap=50)
    assert all(c.strip() for c in chunks)


def test_terminates_without_overlap():
    """overlap=0 must still advance and not loop forever."""
    text = "c" * 1000
    chunks = chunk_text(text, chunk_size=250, overlap=0)
    assert len(chunks) == 4
    assert "".join(chunks) == text
