"""Retrieve relevant KB chunks for a user query."""

from __future__ import annotations
import logging
from dataclasses import dataclass
from typing import Any
from rag.embeddings import VectorStore

logger = logging.getLogger(__name__)

DEFAULT_TOP_K = 5
# Lowered from 0.3 — MiniLM scores paraphrased action queries at 0.25-0.32.
# 0.20 is safe; genuine off-topic queries still score < 0.15.
MIN_SIMILARITY_THRESHOLD = 0.20

# --------------------------------------------------------------------------- #
# Query expansion: common support phrasings mapped to canonical KB terms.     #
# Add more as you discover misses in production.                               #
# --------------------------------------------------------------------------- #
_EXPANSION_ALIASES: dict[str, list[str]] = {
    # account deletion synonyms
    "delete": ["remove account", "close account", "cancel account", "permanently delete"],
    "remove account": ["delete account", "close account"],
    "cancel": ["delete account", "remove account", "close account"],
    "deactivate": ["delete account", "remove account"],
    # profile synonyms
    "update profile": ["edit profile", "change profile", "profile settings"],
    "change email": ["update email", "edit email", "new email address"],
    # password synonyms
    "reset password": ["forgot password", "change password", "update password"],
    "forgot password": ["reset password", "change password"],
    # 2fa synonyms
    "two factor": ["2fa", "two-factor authentication", "enable 2fa"],
    "mfa": ["2fa", "two-factor authentication"],
}


def _expand_query(query: str) -> list[str]:
    """
    Return the original query plus any alias expansions.
    Keeps the list short to avoid noise; deduplicates.
    """
    q_lower = query.lower()
    expansions: list[str] = [query]  # always include original

    for trigger, aliases in _EXPANSION_ALIASES.items():
        if trigger in q_lower:
            for alias in aliases:
                candidate = f"{query} {alias}"
                if candidate not in expansions:
                    expansions.append(candidate)
            break  # one expansion pass is enough per query

    return expansions


@dataclass
class RetrievedChunk:
    """A chunk returned from semantic search."""
    chunk_id: str
    source_filename: str
    section_heading: str
    content: str
    similarity: float


@dataclass
class RetrievalResult:
    """Aggregated retrieval output with scoring signals."""
    chunks: list[RetrievedChunk]
    avg_similarity: float
    supporting_chunk_count: int

    def format_context_blocks(self) -> list[str]:
        blocks = []
        for chunk in self.chunks:
            blocks.append(
                f"[Source: {chunk.source_filename} > {chunk.section_heading}]\n"
                f"{chunk.content}"
            )
        return blocks

    def unique_citations(self) -> list[tuple[str, str]]:
        seen: set[tuple[str, str]] = set()
        citations: list[tuple[str, str]] = []
        for chunk in self.chunks:
            key = (chunk.source_filename, chunk.section_heading)
            if key not in seen:
                seen.add(key)
                citations.append(key)
        return citations


class Retriever:
    """Semantic retriever backed by ChromaDB, with lightweight query expansion."""

    def __init__(
        self,
        vector_store: VectorStore,
        top_k: int = DEFAULT_TOP_K,
        min_similarity: float = MIN_SIMILARITY_THRESHOLD,
    ) -> None:
        self.vector_store = vector_store
        self.top_k = top_k
        self.min_similarity = min_similarity

    def retrieve(self, query: str) -> RetrievalResult:
        """
        Retrieve top-k chunks and compute retrieval metrics.

        Strategy:
        1. Expand the query into 1–N variants (original + alias augmentations).
        2. Run each variant through the vector store.
        3. Merge hits, keeping the best similarity score per chunk_id.
        4. Filter by min_similarity and sort descending.
        """
        query_variants = _expand_query(query)
        logger.info(
            "Query variants for %r: %s",
            query[:60],
            query_variants,
        )

        # chunk_id → best hit dict
        best_hits: dict[str, dict[str, Any]] = {}

        for variant in query_variants:
            raw_hits = self.vector_store.query(variant, top_k=self.top_k)
            for hit in raw_hits:
                cid = hit["chunk_id"]
                if cid not in best_hits or hit["similarity"] > best_hits[cid]["similarity"]:
                    best_hits[cid] = hit

        logger.info(
            "Merged retrieval for query=%r → %d unique chunks across %d variant(s)",
            query[:60],
            len(best_hits),
            len(query_variants),
        )

        # Filter, build typed chunks, sort by similarity desc
        chunks: list[RetrievedChunk] = []
        for hit in sorted(best_hits.values(), key=lambda h: h["similarity"], reverse=True):
            similarity = hit["similarity"]
            if similarity < self.min_similarity:
                continue

            meta: dict[str, Any] = hit.get("metadata", {})
            chunks.append(
                RetrievedChunk(
                    chunk_id=hit["chunk_id"],
                    source_filename=meta.get("source_filename", "unknown"),
                    section_heading=meta.get("section_heading", "Unknown"),
                    content=hit["content"],
                    similarity=similarity,
                )
            )
            logger.debug(
                "Accepted chunk_id=%s similarity=%.3f source=%s",
                hit["chunk_id"],
                similarity,
                meta.get("source_filename"),
            )

        # Trim to top_k after merging
        chunks = chunks[: self.top_k]

        avg_sim = sum(c.similarity for c in chunks) / len(chunks) if chunks else 0.0

        return RetrievalResult(
            chunks=chunks,
            avg_similarity=avg_sim,
            supporting_chunk_count=len(chunks),
        )