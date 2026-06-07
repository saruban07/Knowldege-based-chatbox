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


# ── Token helpers ─────────────────────────────────────────────────────────────

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


# ── Alias extraction ──────────────────────────────────────────────────────────

def _extract_aliases(body: str) -> tuple[list[str], str]:
    """
    Find an 'Also known as' bullet block inside a section body.
    Returns (aliases, body_without_aliases).

    The alias block looks like:
        Also known as:
        - Remove account
        - Close account
        ...

    We strip it out of the body so it doesn't get split away by the token
    chunker, then prepend it to EVERY sub-chunk so retrieval always finds it.
    """
    aliases: list[str] = []
    clean_lines: list[str] = []
    in_aka = False

    for line in body.splitlines():
        stripped = line.strip()
        if re.match(r"also\s+known\s+as", stripped, re.IGNORECASE):
            in_aka = True
            continue                       # drop the "Also known as:" header line
        if in_aka:
            if stripped.startswith("-"):
                aliases.append(stripped.lstrip("-").strip())
                continue                   # consume alias bullet
            else:
                in_aka = False             # end of alias block; fall through

        clean_lines.append(line)

    return aliases, "\n".join(clean_lines).strip()


def _build_chunk_content(heading: str, aliases: list[str], body: str) -> str:
    """
    Prepend heading + alias block to a body fragment so that every sub-chunk
    is independently retrievable by any of its alias phrasings.
    """
    parts = [heading]
    if aliases:
        parts.append("Also known as: " + ", ".join(aliases))
    parts.append(body)
    return "\n".join(parts).strip()


# ── Markdown section parser ───────────────────────────────────────────────────

def _extract_title(content: str, filename: str) -> str:
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return Path(filename).stem.replace("-", " ").title()


def _parse_sections(content: str) -> list[tuple[str, str]]:
    """
    Split markdown into (heading, body) pairs on ## / ### boundaries.
    Top-level # headings are skipped (they're the doc title, not content).
    """
    lines = content.splitlines()
    sections: list[tuple[str, str]] = []
    current_heading = "Introduction"
    current_lines: list[str] = []
    heading_pattern = re.compile(r"^(#{1,3})\s+(.+)$")

    for line in lines:
        match = heading_pattern.match(line.strip())
        if match and len(match.group(1)) >= 2:   # ## or ###
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


# ── Public API ────────────────────────────────────────────────────────────────

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

            # ── KEY FIX: pull aliases out before token-splitting ──────────────
            aliases, clean_body = _extract_aliases(section_body)
            if aliases:
                logger.debug(
                    "%s > %r — found %d aliases: %s",
                    md_file.name, section_heading, len(aliases), aliases,
                )

            sub_chunks = _split_by_tokens(clean_body)

            # If body was empty after stripping aliases, still index the aliases
            if not sub_chunks and aliases:
                sub_chunks = [", ".join(aliases)]

            for sub in sub_chunks:
                # Aliases are prepended to EVERY sub-chunk so retrieval hits
                # them regardless of which fragment a query matches.
                full_content = _build_chunk_content(section_heading, aliases, sub)

                chunk_id = f"{md_file.stem}::{section_heading}::{chunk_index}"
                all_chunks.append(
                    DocumentChunk(
                        chunk_id=chunk_id,
                        source_filename=md_file.name,
                        section_heading=section_heading,
                        title=title,
                        content=full_content,
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