from __future__ import annotations

import time
from collections.abc import Iterator

from core.config import settings
from core.storage import SQLiteStore


def poll_latest_state(mode: str = "controlled", interval_seconds: float = 1.0) -> Iterator[dict | None]:
    """Simple polling adapter retained behind a websocket-like interface.

    SQLite is intentionally used for the PoC because it is reliable across the
    EnergyPlus, MCP, agent, and Streamlit processes without another service.
    """
    store = SQLiteStore(settings.db_path)
    while True:
        yield store.latest_state(mode)
        time.sleep(max(0.1, interval_seconds))
