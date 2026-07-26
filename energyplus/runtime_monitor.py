from __future__ import annotations

from pathlib import Path
from threading import Lock

from core.storage import SQLiteStore


class RuntimeMonitor:
    def __init__(self, store: SQLiteStore, mode: str, log_path: Path):
        self.store = store
        self.mode = mode
        self.log_path = log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.warning_count = 0
        self.severe_count = 0
        self.fatal_count = 0
        self.progress = 0
        self.last_message = ""
        self._lock = Lock()

    def on_message(self, raw_message: bytes) -> None:
        message = raw_message.decode("utf-8", errors="replace").strip()
        if not message:
            return
        with self._lock:
            self.last_message = message[-500:]
            with self.log_path.open("a", encoding="utf-8") as file:
                file.write(message + "\n")
        upper = message.upper()
        if "** WARNING **" in upper:
            self.warning_count += 1
            self.store.log_event("WARNING", f"energyplus:{self.mode}", message[-1000:])
        elif "** SEVERE **" in upper:
            self.severe_count += 1
            self.store.log_event("ERROR", f"energyplus:{self.mode}", message[-1000:])
        elif "** FATAL **" in upper:
            self.fatal_count += 1
            self.store.log_event("CRITICAL", f"energyplus:{self.mode}", message[-1000:])

    def on_progress(self, progress: int) -> None:
        self.progress = int(progress)

    def summary(self) -> dict:
        return {
            "progress_pct": self.progress,
            "warning_count": self.warning_count,
            "severe_count": self.severe_count,
            "fatal_count": self.fatal_count,
            "last_message": self.last_message,
        }
