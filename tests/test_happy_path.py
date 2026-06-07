"""
Happy path tests for the Discord KB Support Bot.
Run with: pytest tests/ -v
"""
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── Make sure project root is on path ────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# =============================================================================
# 1. LOADER — KB chunking and alias extraction
# =============================================================================

from rag.loader import DocumentChunk, _extract_aliases, _parse_sections, load_kb_documents


class TestLoader:

    def test_document_chunk_fields(self):
        """DocumentChunk holds all required fields."""
        chunk = DocumentChunk(
            chunk_id="test::Introduction::0",
            source_filename="test.md",
            section_heading="Introduction",
            title="Test Article",
            content="This is the content.",
        )
        assert chunk.chunk_id == "test::Introduction::0"
        assert chunk.source_filename == "test.md"
        assert chunk.content == "This is the content."

    def test_parse_sections_splits_on_headings(self):
        """Markdown is split into sections by ## headings."""
        md = (
            "# My Article\n\n"
            "## Section One\nContent one.\n\n"
            "## Section Two\nContent two.\n"
        )
        sections = _parse_sections(md)
        headings = [h for h, _ in sections]
        assert "Section One" in headings
        assert "Section Two" in headings

    def test_extract_aliases_returns_list(self):
        """'Also known as' bullets are extracted correctly."""
        body = (
            "Also known as:\n"
            "- Remove account\n"
            "- Close account\n"
            "- Cancel my account\n\n"
            "1. Go to Settings > Danger Zone.\n"
        )
        aliases, clean = _extract_aliases(body)
        assert "Remove account" in aliases
        assert "Close account" in aliases
        assert "Cancel my account" in aliases
        # Alias block should be stripped from the clean body
        assert "Also known as" not in clean

    def test_aliases_prepended_to_chunk_content(self):
        """Aliases appear in the final chunk content so retrieval finds them."""
        with tempfile.TemporaryDirectory() as tmpdir:
            kb_file = Path(tmpdir) / "account.md"
            kb_file.write_text(
                "# Account Management\n\n"
                "## Deleting Your Account\n"
                "Also known as:\n"
                "- Remove account\n"
                "- Close account\n\n"
                "1. Go to Settings > Danger Zone.\n",
                encoding="utf-8",
            )
            chunks = load_kb_documents(tmpdir)
            delete_chunks = [c for c in chunks if "Deleting" in c.section_heading]
            assert delete_chunks, "Expected at least one chunk for Deleting Your Account"
            combined = " ".join(c.content for c in delete_chunks)
            assert "Remove account" in combined
            assert "Close account" in combined

    def test_load_kb_documents_returns_chunks(self):
        """load_kb_documents returns a non-empty list for a valid KB directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "test.md").write_text(
                "# Test\n\n## Section\nSome content here.\n",
                encoding="utf-8",
            )
            chunks = load_kb_documents(tmpdir)
            assert len(chunks) > 0
            assert all(isinstance(c, DocumentChunk) for c in chunks)

    def test_empty_kb_directory_returns_empty_list(self):
        """No MD files → empty list, no crash."""
        with tempfile.TemporaryDirectory() as tmpdir:
            chunks = load_kb_documents(tmpdir)
            assert chunks == []


# =============================================================================
# 2. RETRIEVER — query expansion and similarity filtering
# =============================================================================

from rag.retriever import Retriever, RetrievalResult, _expand_query


class TestQueryExpansion:

    def test_original_query_always_included(self):
        """The original query is always the first variant."""
        variants = _expand_query("how do I reset my password")
        assert variants[0] == "how do I reset my password"

    def test_delete_trigger_expands(self):
        """'delete' trigger produces additional variants."""
        variants = _expand_query("how to delete my account")
        assert len(variants) > 1
        combined = " ".join(variants)
        assert "remove account" in combined or "close account" in combined

    def test_no_trigger_returns_single_variant(self):
        """Query with no known trigger returns only the original."""
        variants = _expand_query("hello there")
        assert variants == ["hello there"]

    def test_retriever_filters_below_threshold(self):
        """Chunks below min_similarity are excluded from results."""
        mock_store = MagicMock()
        mock_store.query.return_value = [
            {
                "chunk_id": "a::0",
                "content": "Some content",
                "metadata": {"source_filename": "a.md", "section_heading": "A"},
                "similarity": 0.10,   # below threshold
                "distance": 1.8,
            }
        ]
        retriever = Retriever(mock_store, top_k=5, min_similarity=0.20)
        result = retriever.retrieve("test query")
        assert result.supporting_chunk_count == 0
        assert result.chunks == []

    def test_retriever_accepts_above_threshold(self):
        """Chunks above min_similarity are included in results."""
        mock_store = MagicMock()
        mock_store.query.return_value = [
            {
                "chunk_id": "b::0",
                "content": "Reset your password here.",
                "metadata": {"source_filename": "pw.md", "section_heading": "Password Reset"},
                "similarity": 0.85,
                "distance": 0.30,
            }
        ]
        retriever = Retriever(mock_store, top_k=5, min_similarity=0.20)
        result = retriever.retrieve("reset password")
        assert result.supporting_chunk_count == 1
        assert result.chunks[0].source_filename == "pw.md"

    def test_retrieval_result_avg_similarity(self):
        """avg_similarity is computed correctly across chunks."""
        mock_store = MagicMock()
        mock_store.query.return_value = [
            {"chunk_id": "a::0", "content": "A", "metadata": {"source_filename": "a.md", "section_heading": "A"}, "similarity": 0.80, "distance": 0.4},
            {"chunk_id": "b::0", "content": "B", "metadata": {"source_filename": "b.md", "section_heading": "B"}, "similarity": 0.60, "distance": 0.8},
        ]
        retriever = Retriever(mock_store, top_k=5, min_similarity=0.20)
        result = retriever.retrieve("test")
        assert abs(result.avg_similarity - 0.70) < 0.01


# =============================================================================
# 3. LLM — JSON parsing and confidence scoring
# =============================================================================

from rag.llm import _parse_llm_json, compute_confidence


class TestJsonParsing:

    def test_parses_clean_json(self):
        """Clean JSON response is parsed correctly."""
        raw = '{"answer": "Do X then Y.", "llm_confidence": 0.9, "citations": []}'
        result = _parse_llm_json(raw)
        assert result["answer"] == "Do X then Y."
        assert result["llm_confidence"] == 0.9

    def test_strips_markdown_fences(self):
        """JSON wrapped in ```json fences is parsed correctly."""
        raw = '```json\n{"answer": "Step 1.", "llm_confidence": 0.8, "citations": []}\n```'
        result = _parse_llm_json(raw)
        assert result["answer"] == "Step 1."

    def test_handles_literal_newline_in_string(self):
        """Literal newline inside JSON string does not crash the parser."""
        raw = '{"answer": "Step 1.\nStep 2.", "llm_confidence": 0.75, "citations": []}'
        result = _parse_llm_json(raw)
        assert "Step 1" in result["answer"]
        assert "Step 2" in result["answer"]

    def test_fallback_on_plain_text(self):
        """Plain text (non-JSON) response is wrapped gracefully."""
        raw = "Here is your answer in plain text."
        result = _parse_llm_json(raw)
        assert "answer" in result
        assert result["llm_confidence"] == 0.4   # degraded confidence

    def test_extracts_json_from_mixed_text(self):
        """JSON block embedded in surrounding prose is extracted."""
        raw = 'Sure! Here you go: {"answer": "Found it.", "llm_confidence": 0.85, "citations": []} Hope that helps!'
        result = _parse_llm_json(raw)
        assert result["answer"] == "Found it."


class TestConfidenceScoring:

    def test_high_confidence_all_signals(self):
        """All strong signals produce a high composite score."""
        score = compute_confidence(
            avg_similarity=0.90,
            supporting_chunks=5,
            llm_confidence=0.95,
        )
        assert score >= 0.75

    def test_low_confidence_poor_retrieval(self):
        """Poor retrieval and low LLM confidence produce a low score."""
        score = compute_confidence(
            avg_similarity=0.15,
            supporting_chunks=0,
            llm_confidence=0.20,
        )
        assert score < 0.40

    def test_score_clamped_between_0_and_1(self):
        """Score is always in [0.0, 1.0]."""
        score = compute_confidence(1.5, 10, 1.5)   # intentionally out of range
        assert 0.0 <= score <= 1.0


# =============================================================================
# 4. TICKET MANAGER — creation and persistence
# =============================================================================

from tickets.manager import Ticket, TicketManager


class TestTicketManager:

    def _make_manager(self, tmpdir):
        path = Path(tmpdir) / "tickets.json"
        return TicketManager(tickets_path=path)

    def test_create_ticket_returns_ticket(self, tmp_path):
        """create_ticket returns a Ticket with correct fields."""
        mgr = self._make_manager(tmp_path)
        ticket = mgr.create_ticket(
            question="How do I reset my password?",
            user_id="123",
            username="sara",
            channel_id="456",
        )
        assert isinstance(ticket, Ticket)
        assert ticket.id == 1001
        assert ticket.question == "How do I reset my password?"
        assert ticket.username == "sara"

    def test_ticket_id_increments(self, tmp_path):
        """Each ticket gets a unique incrementing ID."""
        mgr = self._make_manager(tmp_path)
        t1 = mgr.create_ticket("Q1", "1", "sara", "1")
        t2 = mgr.create_ticket("Q2", "2", "bob",  "1")
        assert t2.id == t1.id + 1

    def test_ticket_persisted_to_json(self, tmp_path):
        """Ticket is saved to the JSON file immediately."""
        mgr = self._make_manager(tmp_path)
        mgr.create_ticket("Test question", "1", "sara", "1")
        raw = json.loads((tmp_path / "tickets.json").read_text())
        assert len(raw["tickets"]) == 1
        assert raw["tickets"][0]["question"] == "Test question"

    def test_ticket_count_property(self, tmp_path):
        """ticket_count reflects the number of tickets created."""
        mgr = self._make_manager(tmp_path)
        assert mgr.ticket_count == 0
        mgr.create_ticket("Q1", "1", "sara", "1")
        mgr.create_ticket("Q2", "2", "bob",  "1")
        assert mgr.ticket_count == 2

    def test_ticket_has_timestamp(self, tmp_path):
        """Created ticket has a non-empty timestamp."""
        mgr = self._make_manager(tmp_path)
        ticket = mgr.create_ticket("Q1", "1", "sara", "1")
        assert ticket.timestamp is not None
        assert "UTC" in ticket.timestamp

    def test_ticket_stores_user_id(self, tmp_path):
        """user_id and channel_id are stored correctly."""
        mgr = self._make_manager(tmp_path)
        ticket = mgr.create_ticket("Q1", "123", "sara", "456")
        assert ticket.user_id == "123"
        assert ticket.channel_id == "456"

    def test_multiple_tickets_persisted(self, tmp_path):
        """All created tickets are saved to JSON."""
        mgr = self._make_manager(tmp_path)
        mgr.create_ticket("Q1", "1", "sara", "1")
        mgr.create_ticket("Q2", "2", "bob",  "1")
        mgr.create_ticket("Q3", "3", "ali",  "1")
        raw = json.loads((tmp_path / "tickets.json").read_text())
        assert len(raw["tickets"]) == 3

    def test_next_id_increments_in_json(self, tmp_path):
        """next_id in JSON increments after each ticket."""
        mgr = self._make_manager(tmp_path)
        mgr.create_ticket("Q1", "1", "sara", "1")
        raw = json.loads((tmp_path / "tickets.json").read_text())
        assert raw["next_id"] == 1002

    def test_format_ticket_message(self, tmp_path):
        """format_ticket_message includes ticket ID and question."""
        mgr = self._make_manager(tmp_path)
        ticket = mgr.create_ticket("How do I reset my password?", "1", "sara", "1")
        msg = mgr.format_ticket_message(ticket)
        assert "#1001" in msg
        assert "How do I reset my password?" in msg