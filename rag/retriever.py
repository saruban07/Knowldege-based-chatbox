"""Retrieve relevant KB chunks for a user query."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from rag.embeddings import VectorStore

logger = logging.getLogger(__name__)

DEFAULT_TOP_K = 5
MIN_SIMILARITY_THRESHOLD = 0.3


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
    """Semantic retriever backed by ChromaDB."""

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
        """Retrieve top-k chunks and compute retrieval metrics."""
        raw_hits = self.vector_store.query(query, top_k=self.top_k)
        logger.info(
            "Retrieval for query=%r returned %d hits",
            query[:80],
            len(raw_hits),
        )

        chunks: list[RetrievedChunk] = []
        for hit in raw_hits:
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
                "Hit chunk_id=%s similarity=%.3f source=%s",
                hit["chunk_id"],
                similarity,
                meta.get("source_filename"),
            )

        if chunks:
            avg_sim = sum(c.similarity for c in chunks) / len(chunks)
        else:
            avg_sim = 0.0

        return RetrievalResult(
            chunks=chunks,
            avg_similarity=avg_sim,
            supporting_chunk_count=len(chunks),
        )
