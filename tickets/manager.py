"""Support ticket persistence and creation."""
from __future__ import annotations
import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_TICKETS_PATH = Path("tickets/tickets.json")


@dataclass
class Ticket:
    id: int
    question: str
    user_id: str
    username: str
    channel_id: str
    timestamp: str


class TicketManager:
    """Create and persist support tickets to JSON."""

    def __init__(self, tickets_path: Path | str = DEFAULT_TICKETS_PATH) -> None:
        self.tickets_path = Path(tickets_path)
        self._data: dict = {"next_id": 1001, "tickets": []}
        self._load()

    def _load(self) -> None:
        if not self.tickets_path.exists():
            self.tickets_path.parent.mkdir(parents=True, exist_ok=True)
            self._save()
            return
        try:
            raw = self.tickets_path.read_text(encoding="utf-8")
            self._data = json.loads(raw) if raw.strip() else {"next_id": 1001, "tickets": []}
        except (OSError, json.JSONDecodeError) as exc:
            logger.error("Failed to load tickets from %s: %s", self.tickets_path, exc)
            self._data = {"next_id": 1001, "tickets": []}

    def _save(self) -> None:
        self.tickets_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.tickets_path.write_text(
                json.dumps(self._data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError as exc:
            logger.error("Failed to save tickets: %s", exc)
            raise

    @property
    def ticket_count(self) -> int:
        return len(self._data.get("tickets", []))

    # ── NEW: used by !analytics and !tickets ─────────────────────────────────

    @property
    def all_tickets(self) -> list[Ticket]:
        return [Ticket(**t) for t in self._data.get("tickets", [])]

    def get_analytics(self) -> dict[str, Any]:
        """Return summary stats for !analytics command."""
        tickets = self.all_tickets
        total = len(tickets)
        if total == 0:
            return {"total": 0, "this_week": 0, "top_topics": []}

        # Tickets created in the last 7 days
        now = datetime.now(timezone.utc)
        fmt = "%Y-%m-%d %H:%M:%S UTC"
        this_week = 0
        for t in tickets:
            try:
                created = datetime.strptime(t.timestamp, fmt).replace(tzinfo=timezone.utc)
                if (now - created).days <= 7:
                    this_week += 1
            except ValueError:
                pass

        # Top 3 most common first words as a rough topic hint
        from collections import Counter
        words = []
        for t in tickets:
            first = t.question.strip().split()
            if first:
                words.append(first[0].lower().strip("?!.,"))
        top_topics = [w for w, _ in Counter(words).most_common(3)]

        return {
            "total":      total,
            "this_week":  this_week,
            "top_topics": top_topics,
        }

    # ── Existing methods unchanged ────────────────────────────────────────────

    def create_ticket(
        self,
        question: str,
        user_id: str,
        username: str,
        channel_id: str,
    ) -> Ticket:
        ticket_id = int(self._data.get("next_id", 1001))
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        ticket = Ticket(
            id=ticket_id,
            question=question,
            user_id=str(user_id),
            username=username,
            channel_id=str(channel_id),
            timestamp=timestamp,
        )
        self._data.setdefault("tickets", []).append(asdict(ticket))
        self._data["next_id"] = ticket_id + 1
        self._save()
        logger.info(
            "Created ticket #%d for user=%s question=%r",
            ticket_id, username, question[:80],
        )
        return ticket

    def format_ticket_message(self, ticket: Ticket) -> str:
        return (
            f"**Ticket #{ticket.id}**\n"
            f"**Question:** {ticket.question}\n"
            f"**Timestamp:** {ticket.timestamp}"
        )



