"""Load and chunk Markdown knowledge-base articles."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import tiktoken

logger = logging.getLogger(__name__)

DEFAULT_KB_DIR = Path("kb")
MAX_CHUNK_TOKENS = 512
CHUNK_OVERLAP_TOKENS = 64


@dataclass(frozen=True)
class DocumentChunk:
    """A single indexed chunk from a KB article."""

    chunk_id: str
    source_filename: str
    section_heading: str
    title: str
    content: str


def _count_tokens(text: str, encoding_name: str = "cl100k_base") -> int:
    try:
        enc = tiktoken.get_encoding(encoding_name)
        return len(enc.encode(text))
    except Exception:
        return len(text) // 4


def _split_by_tokens(
    text: str,
    max_tokens: int = MAX_CHUNK_TOKENS,
    overlap_tokens: int = CHUNK_OVERLAP_TOKENS,
) -> list[str]:
    """Split long text into overlapping token-bounded chunks."""
    enc = tiktoken.get_encoding("cl100k_base")
    tokens = enc.encode(text)
    if len(tokens) <= max_tokens:
        return [text.strip()] if text.strip() else []

    chunks: list[str] = []
    start = 0
    while start < len(tokens):
        end = min(start + max_tokens, len(tokens))
        chunk_text = enc.decode(tokens[start:end]).strip()
        if chunk_text:
            chunks.append(chunk_text)
        if end >= len(tokens):
            break
        start = max(0, end - overlap_tokens)
    return chunks


def _extract_title(content: str, filename: str) -> str:
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return Path(filename).stem.replace("-", " ").title()


def _parse_sections(content: str) -> list[tuple[str, str]]:
    """
    Split markdown into sections by headings (## and ###).
    Returns list of (heading, body) tuples.
    """
    lines = content.splitlines()
    sections: list[tuple[str, str]] = []
    current_heading = "Introduction"
    current_lines: list[str] = []

    heading_pattern = re.compile(r"^(#{1,3})\s+(.+)$")

    for line in lines:
        match = heading_pattern.match(line.strip())
        if match and len(match.group(1)) >= 2:
            if current_lines:
                body = "\n".join(current_lines).strip()
                if body:
                    sections.append((current_heading, body))
            current_heading = match.group(2).strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        body = "\n".join(current_lines).strip()
        if body:
            sections.append((current_heading, body))

    if not sections and content.strip():
        sections.append(("Introduction", content.strip()))

    return sections


def load_kb_documents(kb_dir: Path | str = DEFAULT_KB_DIR) -> list[DocumentChunk]:
    """Load all Markdown files from the KB directory and chunk them."""
    kb_path = Path(kb_dir)
    if not kb_path.exists():
        logger.warning("KB directory does not exist: %s", kb_path)
        return []

    md_files = sorted(kb_path.glob("*.md"))
    if not md_files:
        logger.warning("No Markdown files found in %s", kb_path)
        return []

    all_chunks: list[DocumentChunk] = []

    for md_file in md_files:
        try:
            content = md_file.read_text(encoding="utf-8")
        except OSError as exc:
            logger.error("Failed to read %s: %s", md_file, exc)
            continue

        if not content.strip():
            logger.warning("Skipping empty file: %s", md_file.name)
            continue

        title = _extract_title(content, md_file.name)
        sections = _parse_sections(content)

        chunk_index = 0
        for section_heading, section_body in sections:
            sub_chunks = _split_by_tokens(section_body)
            for sub in sub_chunks:
                chunk_id = f"{md_file.stem}::{section_heading}::{chunk_index}"
                all_chunks.append(
                    DocumentChunk(
                        chunk_id=chunk_id,
                        source_filename=md_file.name,
                        section_heading=section_heading,
                        title=title,
                        content=sub,
                    )
                )
                chunk_index += 1

        logger.info(
            "Loaded %s: %d chunks from %d sections",
            md_file.name,
            chunk_index,
            len(sections),
        )

    return all_chunks


def iter_kb_filenames(kb_dir: Path | str = DEFAULT_KB_DIR) -> Iterator[str]:
    """Yield names of all .md files in the KB directory."""
    kb_path = Path(kb_dir)
    if not kb_path.exists():
        return
    for md_file in sorted(kb_path.glob("*.md")):
        yield md_file.name
