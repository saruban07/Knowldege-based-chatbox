"""Local ONNX embedding generation and ChromaDB vector store."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings
from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2

from rag.loader import DocumentChunk

logger = logging.getLogger(__name__)

DEFAULT_CHROMA_DIR = Path("chroma_db")
COLLECTION_NAME = "kb_chunks"
DEFAULT_EMBEDDING_MODEL = "all-MiniLM-L6-v2"


class LocalEmbedder:
    """Embeddings via ChromaDB's bundled ONNX model (runs locally, no API key)."""

    def __init__(self, model_name: str = DEFAULT_EMBEDDING_MODEL) -> None:
        if model_name != DEFAULT_EMBEDDING_MODEL:
            logger.warning(
                "Only %s is supported for local ONNX embeddings; using it instead of %s",
                DEFAULT_EMBEDDING_MODEL,
                model_name,
            )
        print(f"  Loading local embeddings ({DEFAULT_EMBEDDING_MODEL})...", flush=True)
        logger.info("Initializing local ONNX embeddings: %s", DEFAULT_EMBEDDING_MODEL)
        self._model = ONNXMiniLM_L6_V2()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._model(texts)

    def embed_query(self, text: str) -> list[float]:
        return self._model([text])[0]


class VectorStore:
    """Manages document embeddings in ChromaDB."""

    def __init__(
        self,
        persist_dir: Path | str = DEFAULT_CHROMA_DIR,
        collection_name: str = COLLECTION_NAME,
        embedding_model: str | None = None,
    ) -> None:
        self.persist_dir = Path(persist_dir)
        self.collection_name = collection_name
        self.embedding_model = embedding_model or os.getenv(
            "EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL
        )

        self._embeddings: LocalEmbedder | None = None
        self._client = chromadb.PersistentClient(
            path=str(self.persist_dir),
            settings=Settings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def _get_embedder(self) -> LocalEmbedder:
        if self._embeddings is None:
            self._embeddings = LocalEmbedder(self.embedding_model)
        return self._embeddings

    @property
    def chunk_count(self) -> int:
        return self._collection.count()

    def clear(self) -> None:
        """Remove all vectors from the collection."""
        try:
            self._client.delete_collection(self.collection_name)
        except Exception:
            pass
        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("Cleared vector collection: %s", self.collection_name)

    def index_chunks(self, chunks: list[DocumentChunk], batch_size: int = 32) -> int:
        """Embed and store chunks. Returns number of indexed chunks."""
        if not chunks:
            logger.warning("No chunks to index")
            return 0

        embedder = self._get_embedder()
        self.clear()
        total = 0
        total_batches = (len(chunks) + batch_size - 1) // batch_size

        for batch_num, i in enumerate(range(0, len(chunks), batch_size), start=1):
            batch = chunks[i : i + batch_size]
            texts = [c.content for c in batch]
            ids = [c.chunk_id for c in batch]
            metadatas: list[dict[str, Any]] = [
                {
                    "source_filename": c.source_filename,
                    "section_heading": c.section_heading,
                    "title": c.title,
                    "chunk_id": c.chunk_id,
                }
                for c in batch
            ]

            print(
                f"  Indexing batch {batch_num}/{total_batches} "
                f"({len(batch)} chunks locally)...",
                flush=True,
            )
            sys.stdout.flush()

            try:
                vectors = embedder.embed_documents(texts)
            except Exception as exc:
                logger.error("Embedding batch failed at offset %d: %s", i, exc)
                raise

            self._collection.add(
                ids=ids,
                embeddings=vectors,
                documents=texts,
                metadatas=metadatas,
            )
            total += len(batch)

        logger.info("Indexed %d chunks into ChromaDB", total)
        return total

    def query(
        self,
        query_text: str,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Semantic search over indexed chunks.
        Returns list of dicts with content, metadata, and similarity score.
        """
        if self._collection.count() == 0:
            logger.warning("Vector store is empty; run reindex first")
            return []

        try:
            query_vector = self._get_embedder().embed_query(query_text)
        except Exception as exc:
            logger.error("Query embedding failed: %s", exc)
            raise

        try:
            results = self._collection.query(
                query_embeddings=[query_vector],
                n_results=min(top_k, self._collection.count()),
                include=["documents", "metadatas", "distances"],
            )
        except Exception as exc:
            logger.error("ChromaDB query failed: %s", exc)
            raise

        hits: list[dict[str, Any]] = []
        if not results["ids"] or not results["ids"][0]:
            return hits

        for doc_id, document, metadata, distance in zip(
            results["ids"][0],
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            similarity = max(0.0, 1.0 - (distance / 2.0))
            hits.append(
                {
                    "chunk_id": doc_id,
                    "content": document,
                    "metadata": metadata or {},
                    "distance": distance,
                    "similarity": similarity,
                }
            )

        return hits
