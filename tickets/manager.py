"""Support ticket persistence and creation."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

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
            ticket_id,
            username,
            question[:80],
        )
        return ticket

  