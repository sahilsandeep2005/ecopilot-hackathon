from __future__ import annotations

from core.config import settings
from core.storage import SQLiteStore


class AgentMemory:
    def __init__(self):
        self.store = SQLiteStore(settings.db_path)

    def record_cycle(self, message: str, payload: dict | None = None) -> None:
        self.store.log_event("INFO", "agent", message, payload)

    def record_error(self, message: str, payload: dict | None = None) -> None:
        self.store.log_event("ERROR", "agent", message, payload)

    def recent(self, limit: int = 20) -> list[dict]:
        return self.store.events(limit=limit)
