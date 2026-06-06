from __future__ import annotations

import re
from pathlib import Path


def load_transcript(path: str | Path) -> str:
    """Load a transcript from a .txt file and perform minimal cleaning."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Transcript not found: {p}")
    if p.suffix.lower() not in {".txt", ".md"}:
        raise ValueError(f"Unsupported format '{p.suffix}'. Provide a .txt file.")

    raw = p.read_text(encoding="utf-8")
    return _clean(raw)


def _clean(text: str) -> str:
    # Collapse excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Strip trailing whitespace per line
    lines = [line.rstrip() for line in text.splitlines()]
    return "\n".join(lines).strip()


def split_into_chunks(text: str, max_chars: int = 90_000) -> list[str]:
    """Split long transcripts into overlapping chunks for LLM context limits.

    Most transcripts fit in one chunk; this is a safety net for very long calls.
    """
    if len(text) <= max_chars:
        return [text]

    chunks: list[str] = []
    overlap = 2_000
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = end - overlap
    return chunks
