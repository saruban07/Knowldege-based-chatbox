"""LLM answer generation via Groq API."""

from __future__ import annotations
import json
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from rag.embeddings import VectorStore
from rag.loader import DEFAULT_KB_DIR, load_kb_documents
from rag.retriever import Retriever

logger = logging.getLogger(__name__)

WEIGHT_RETRIEVAL = 0.40
WEIGHT_CHUNK_SUPPORT = 0.25
WEIGHT_LLM = 0.35
MAX_SUPPORTING_CHUNKS = 5
DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"

# ── System prompt (no prompts.py needed) ─────────────────────────────────────
SYSTEM_PROMPT = (
    "You are a helpful customer support assistant. "
    "Answer the user's question using ONLY the context provided. "
    "If the context does not contain enough information, say so honestly.\n\n"
    "IMPORTANT: Respond with ONLY a single valid JSON object — no prose, "
    "no markdown outside the JSON, no extra keys.\n"
    "Use \\n (two characters: backslash + n) for line breaks inside string values. "
    "NEVER use a literal newline character inside a JSON string value.\n\n"
    "Required format:\n"
    "{\n"
    '  "answer": "Your answer here. Use \\n for line breaks.",\n'
    '  "llm_confidence": 0.9,\n'
    '  "citations": [\n'
    '    {"source": "filename.md", "section": "Section Name"}\n'
    "  ]\n"
    "}"
)


def build_user_prompt(question: str, context_blocks: list[str]) -> str:
    context = "\n\n".join(context_blocks)
    return (
        f"Context from knowledge base:\n\n{context}\n\n"
        f"User question: {question}\n\n"
        "Answer using only the context above. "
        "Respond with a JSON object as specified."
    )


# ── JSON parsing ──────────────────────────────────────────────────────────────

def _escape_control_chars_in_strings(text: str) -> str:
    """
    Walk JSON text char-by-char. Inside quoted strings, replace literal
    control characters with their escape sequences so json.loads() doesn't crash.
    This fixes: 'Invalid control character at line N column M'
    """
    result = []
    in_string = False
    escape_next = False

    for ch in text:
        if escape_next:
            result.append(ch)
            escape_next = False
            continue
        if ch == "\\" and in_string:
            result.append(ch)
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            result.append(ch)
            continue
        if in_string:
            if ch == "\n":
                result.append("\\n")
            elif ch == "\r":
                result.append("\\r")
            elif ch == "\t":
                result.append("\\t")
            elif ord(ch) < 0x20:
                pass  # drop other stray control chars
            else:
                result.append(ch)
        else:
            result.append(ch)

    return "".join(result)


def _parse_llm_json(text: str) -> dict[str, Any]:
    """
    Robustly extract and parse JSON from an LLM response.

    Fallback chain:
      1. Strip markdown fences → sanitize control chars → json.loads()
      2. Find first {...} block → sanitize → json.loads()
      3. Treat whole response as plain-text answer (degraded confidence)
    """
    cleaned = text.strip()

    # Step 1 — strip ```json ... ``` fences
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", cleaned)
    if fence_match:
        cleaned = fence_match.group(1).strip()

    # Step 2 — sanitize literal control characters inside JSON strings
    cleaned = _escape_control_chars_in_strings(cleaned)

    # Attempt A — parse the full sanitized text
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Attempt B — find the first { ... } block and parse that
    brace_match = re.search(r"\{[\s\S]*\}", cleaned)
    if brace_match:
        try:
            return json.loads(brace_match.group())
        except json.JSONDecodeError:
            pass

    # Attempt C — model returned plain prose, not JSON; wrap it gracefully
    logger.warning("LLM returned non-JSON output; wrapping as plain-text answer")
    plain = re.sub(r"[`*#]", "", text).strip()
    return {
        "answer": plain[:1500] if plain else "I was unable to process that request.",
        "llm_confidence": 0.4,
        "citations": [],
    }


# ── Citation helpers ──────────────────────────────────────────────────────────

def _format_citations(citations: list[tuple[str, str]]) -> str:
    if not citations:
        return ""
    lines = ["", "**Sources:**", ""]
    for source, section in citations:
        lines.append(f"• {source} > {section}")
    return "\n".join(lines)


def _merge_citations(
    llm_citations: list[dict[str, str]],
    retrieval_citations: list[tuple[str, str]],
) -> list[tuple[str, str]]:
    merged: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for item in llm_citations:
        source = item.get("source", "")
        section = item.get("section", "")
        if source:
            key = (source, section)
            if key not in seen:
                seen.add(key)
                merged.append(key)
    for key in retrieval_citations:
        if key not in seen:
            seen.add(key)
            merged.append(key)
    return merged


# ── Confidence scoring ────────────────────────────────────────────────────────

def compute_confidence(
    avg_similarity: float,
    supporting_chunks: int,
    llm_confidence: float,
) -> float:
    chunk_score = min(supporting_chunks / MAX_SUPPORTING_CHUNKS, 1.0)
    composite = (
        WEIGHT_RETRIEVAL * avg_similarity
        + WEIGHT_CHUNK_SUPPORT * chunk_score
        + WEIGHT_LLM * llm_confidence
    )
    return round(min(max(composite, 0.0), 1.0), 2)


# ── Groq availability check ───────────────────────────────────────────────────

def check_groq_available(
    api_key: str | None = None,
    model_name: str | None = None,
) -> tuple[bool, str]:
    key = api_key or os.getenv("GROQ_API_KEY", "")
    model = model_name or os.getenv("GROQ_MODEL", DEFAULT_GROQ_MODEL)
    if not key or key.strip() in ("", "your_groq_api_key_here"):
        return False, (
            "GROQ_API_KEY is missing in .env. "
            "Get a free key at https://console.groq.com/keys"
        )
    return True, f"Groq configured (model: {model})"


# ── RAG dataclass ─────────────────────────────────────────────────────────────

@dataclass
class RAGResponse:
    """Structured RAG pipeline output."""
    answer: str
    confidence: float
    citations: list[tuple[str, str]]
    llm_confidence: float
    retrieval_similarity: float
    supporting_chunks: int
    escalated: bool = False


# ── Main service ──────────────────────────────────────────────────────────────

class RAGService:
    """Orchestrates loading, indexing, retrieval, and answer generation."""

    def __init__(
        self,
        kb_dir: Path | str = DEFAULT_KB_DIR,
        chroma_dir: Path | str = "chroma_db",
        model_name: str | None = None,
        groq_api_key: str | None = None,
        confidence_threshold: float = 0.75,
        top_k: int = 5,
    ) -> None:
        self.kb_dir = Path(kb_dir)
        self.model_name = model_name or os.getenv("GROQ_MODEL", DEFAULT_GROQ_MODEL)
        self.groq_api_key = groq_api_key or os.getenv("GROQ_API_KEY", "")
        self.confidence_threshold = confidence_threshold
        self.top_k = top_k
        self.vector_store = VectorStore(persist_dir=chroma_dir)
        self.retriever = Retriever(self.vector_store, top_k=top_k)
        self._llm = ChatGroq(
            model=self.model_name,
            groq_api_key=self.groq_api_key,
            temperature=0.0,
            max_retries=2,
        )
        self._kb_file_count = 0
        self._indexed_chunks = 0

    @property
    def kb_file_count(self) -> int:
        return self._kb_file_count

    @property
    def indexed_chunks(self) -> int:
        return self._indexed_chunks

    def reindex(self) -> tuple[int, int]:
        chunks = load_kb_documents(self.kb_dir)
        self._kb_file_count = len(list(self.kb_dir.glob("*.md"))) if self.kb_dir.exists() else 0
        self._indexed_chunks = self.vector_store.index_chunks(chunks)
        logger.info("Reindex complete: %d files, %d chunks", self._kb_file_count, self._indexed_chunks)
        return self._kb_file_count, self._indexed_chunks

    def initialize(self) -> None:
        self._kb_file_count = len(list(self.kb_dir.glob("*.md"))) if self.kb_dir.exists() else 0
        self._indexed_chunks = self.vector_store.chunk_count
        if self._indexed_chunks == 0 and self._kb_file_count > 0:
            logger.info("Empty vector store; performing initial index")
            print(f"  First run: indexing {self._kb_file_count} KB file(s)...", flush=True)
            self.reindex()
        else:
            logger.info("Using existing index: %d files, %d chunks", self._kb_file_count, self._indexed_chunks)

    async def answer(self, question: str) -> RAGResponse:
        """Run full RAG pipeline for a user question."""
        retrieval = self.retriever.retrieve(question)
        if not retrieval.chunks:
            logger.warning("No relevant chunks for question: %s", question[:80])
            return RAGResponse(
                answer="I couldn't find relevant information in the knowledge base for your question.",
                confidence=0.0,
                citations=[],
                llm_confidence=0.0,
                retrieval_similarity=0.0,
                supporting_chunks=0,
            )

        context_blocks = retrieval.format_context_blocks()
        user_prompt = build_user_prompt(question, context_blocks)

        try:
            response = await self._llm.ainvoke(
                [
                    SystemMessage(content=SYSTEM_PROMPT),
                    HumanMessage(content=user_prompt),
                ]
            )
            content = response.content
            if isinstance(content, list):
                content = "".join(str(part) for part in content)

            # ── This is where the crash was: now uses robust parser ──────────
            parsed = _parse_llm_json(str(content))

        except Exception as exc:
            logger.error("Groq API call failed: %s", exc)
            return RAGResponse(
                answer=(
                    "I'm temporarily unable to process your question. "
                    "Check your GROQ_API_KEY and try again, "
                    "or create a support ticket with `!ticket`."
                ),
                confidence=0.0,
                citations=retrieval.unique_citations(),
                llm_confidence=0.0,
                retrieval_similarity=retrieval.avg_similarity,
                supporting_chunks=retrieval.supporting_chunk_count,
            )

        answer_text = parsed.get("answer", "").strip()
        llm_confidence = float(parsed.get("llm_confidence", 0.5))
        llm_citations = parsed.get("citations", [])
        citations = _merge_citations(llm_citations, retrieval.unique_citations())
        confidence = compute_confidence(
            retrieval.avg_similarity,
            retrieval.supporting_chunk_count,
            llm_confidence,
        )

        logger.info(
            "RAG result confidence=%.2f retrieval=%.2f llm=%.2f chunks=%d",
            confidence, retrieval.avg_similarity, llm_confidence, retrieval.supporting_chunk_count,
        )

        return RAGResponse(
            answer=answer_text,
            confidence=confidence,
            citations=citations,
            llm_confidence=llm_confidence,
            retrieval_similarity=retrieval.avg_similarity,
            supporting_chunks=retrieval.supporting_chunk_count,
        )

    def format_discord_response(
        self,
        rag_response: RAGResponse,
        *,
        include_confidence: bool = True,
    ) -> str:
        parts = [rag_response.answer]
        if rag_response.citations:
            parts.append(_format_citations(rag_response.citations))
        if include_confidence:
            parts.append(f"\n**Confidence:** {rag_response.confidence:.0%}")
        return "\n".join(parts)

    def should_escalate(self, confidence: float) -> bool:
        return confidence < self.confidence_threshold


