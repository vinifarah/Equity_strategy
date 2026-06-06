"""Unit tests for src/ingestion.py — no API calls, no fixtures needed."""
from __future__ import annotations

import pytest

from src.ingestion import _clean, load_transcript, split_into_chunks


# ---------------------------------------------------------------------------
# _clean
# ---------------------------------------------------------------------------


def test_clean_collapses_multiple_blank_lines():
    raw = "Line 1\n\n\n\nLine 2"
    result = _clean(raw)
    assert "\n\n\n" not in result
    assert "Line 1" in result
    assert "Line 2" in result


def test_clean_strips_trailing_whitespace():
    raw = "Hello   \nWorld  "
    result = _clean(raw)
    for line in result.splitlines():
        assert line == line.rstrip()


def test_clean_strips_leading_and_trailing_blank_lines():
    raw = "\n\n  Hello World  \n\n"
    result = _clean(raw)
    assert result.startswith("Hello")
    assert result.endswith("World")


def test_clean_preserves_content():
    raw = "CEO: Good morning. We delivered strong results."
    assert _clean(raw) == raw


# ---------------------------------------------------------------------------
# load_transcript
# ---------------------------------------------------------------------------


def test_load_transcript_reads_txt(tmp_path):
    f = tmp_path / "transcript.txt"
    f.write_text("Hello earnings call\n\nSecond paragraph.", encoding="utf-8")
    result = load_transcript(str(f))
    assert "Hello earnings call" in result
    assert "Second paragraph" in result


def test_load_transcript_accepts_md_extension(tmp_path):
    f = tmp_path / "notes.md"
    f.write_text("# Transcript\nSome text.", encoding="utf-8")
    result = load_transcript(str(f))
    assert "Transcript" in result


def test_load_transcript_raises_on_missing_file():
    with pytest.raises(FileNotFoundError):
        load_transcript("/nonexistent/path/transcript.txt")


def test_load_transcript_raises_on_unsupported_extension(tmp_path):
    f = tmp_path / "doc.pdf"
    f.write_bytes(b"%PDF-1.4")
    with pytest.raises(ValueError, match="Unsupported format"):
        load_transcript(str(f))


def test_load_transcript_cleans_output(tmp_path):
    f = tmp_path / "messy.txt"
    f.write_text("Line 1   \n\n\n\nLine 2\n", encoding="utf-8")
    result = load_transcript(str(f))
    assert "\n\n\n" not in result
    assert not any(line != line.rstrip() for line in result.splitlines())


# ---------------------------------------------------------------------------
# split_into_chunks
# ---------------------------------------------------------------------------


def test_split_single_chunk_when_short():
    text = "A" * 100
    chunks = split_into_chunks(text, max_chars=200)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_split_exact_boundary():
    text = "A" * 90_000
    chunks = split_into_chunks(text, max_chars=90_000)
    assert len(chunks) == 1


def test_split_creates_multiple_chunks_for_long_text():
    text = "A" * 200_000
    chunks = split_into_chunks(text, max_chars=90_000)
    assert len(chunks) > 1


def test_split_chunks_cover_all_content():
    text = "ABCDE" * 40_000  # 200K chars
    chunks = split_into_chunks(text, max_chars=90_000)
    # First chunk starts at 0
    assert chunks[0] == text[: 90_000]
    # Last chunk ends at len(text)
    assert chunks[-1] == text[len(text) - len(chunks[-1]):]


def test_split_overlap_between_chunks():
    text = "X" * 200_000
    overlap = 2_000
    chunks = split_into_chunks(text, max_chars=90_000)
    if len(chunks) > 1:
        # End of chunk[0] and beginning of chunk[1] overlap by ~2000 chars
        tail_0 = chunks[0][-overlap:]
        head_1 = chunks[1][:overlap]
        assert tail_0 == head_1
