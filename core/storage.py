from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Iterable

from core.utils import json_dumps, utc_now_iso


SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;

CREATE TABLE IF NOT EXISTS states (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    mode TEXT NOT NULL,
    sim_step INTEGER NOT NULL,
    sim_time_hours REAL NOT NULL,
    created_at TEXT NOT NULL,
    payload TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_states_mode_step ON states(mode, sim_step);
CREATE INDEX IF NOT EXISTS idx_states_run ON states(run_id, mode);

CREATE TABLE IF NOT EXISTS actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action_id TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    created_for_step INTEGER NOT NULL,
    source TEXT NOT NULL,
    status TEXT NOT NULL,
    approval_token TEXT,
    applied_step INTEGER,
    payload TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_actions_status ON actions(status, id);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    severity TEXT NOT NULL,
    source TEXT NOT NULL,
    message TEXT NOT NULL,
    payload TEXT
);
CREATE INDEX IF NOT EXISTS idx_events_created ON events(id);
"""


class SQLiteStore:
    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.init_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=20.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout=20000")
        return connection

    def _execute_with_retry(self, operation, attempts: int = 6):
        delay = 0.05
        for attempt in range(attempts):
            try:
                return operation()
            except sqlite3.OperationalError as exc:
                if "locked" not in str(exc).lower() or attempt == attempts - 1:
                    raise
                time.sleep(delay)
                delay *= 2

    def init_schema(self) -> None:
        def operation() -> None:
            with self._connect() as connection:
                connection.executescript(SCHEMA)

        self._execute_with_retry(operation)

    def clear_runtime_data(self) -> None:
        def operation() -> None:
            with self._connect() as connection:
                connection.execute("DELETE FROM states")
                connection.execute("DELETE FROM actions")
                connection.execute("DELETE FROM events")

        self._execute_with_retry(operation)

    def insert_state(self, state: dict[str, Any]) -> int:
        payload = json_dumps(state)

        def operation() -> int:
            with self._connect() as connection:
                cursor = connection.execute(
                    """
                    INSERT INTO states(run_id, mode, sim_step, sim_time_hours, created_at, payload)
                    VALUES(?, ?, ?, ?, ?, ?)
                    """,
                    (
                        state["run_id"],
                        state["mode"],
                        int(state["sim_step"]),
                        float(state["sim_time_hours"]),
                        state.get("timestamp_utc", utc_now_iso()),
                        payload,
                    ),
                )
                return int(cursor.lastrowid)

        return self._execute_with_retry(operation)

    @staticmethod
    def _decode_row(row: sqlite3.Row | None) -> dict[str, Any] | None:
        if row is None:
            return None
        value = dict(row)
        if "payload" in value and value["payload"]:
            value["payload"] = json.loads(value["payload"])
        return value

    def latest_state(self, mode: str = "controlled") -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM states WHERE mode=? ORDER BY id DESC LIMIT 1", (mode,)
            ).fetchone()
        decoded = self._decode_row(row)
        return decoded["payload"] if decoded else None

    def recent_states(self, mode: str = "controlled", limit: int = 12) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 1000))
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM states WHERE mode=? ORDER BY id DESC LIMIT ?", (mode, limit)
            ).fetchall()
        result = [self._decode_row(row)["payload"] for row in rows]
        result.reverse()
        return result

    def all_states(self, mode: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT payload FROM states WHERE mode=? ORDER BY id ASC", (mode,)
            ).fetchall()
        return [json.loads(row["payload"]) for row in rows]

    def insert_action(
        self,
        action: dict[str, Any],
        approval_token: str | None,
        status: str = "approved",
    ) -> dict[str, Any]:
        payload = json_dumps(action)

        def operation() -> dict[str, Any]:
            with self._connect() as connection:
                try:
                    cursor = connection.execute(
                        """
                        INSERT INTO actions(
                            action_id, created_at, created_for_step, source,
                            status, approval_token, payload
                        ) VALUES(?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            action["action_id"],
                            utc_now_iso(),
                            int(action.get("created_for_step", 0)),
                            action.get("source", "unknown"),
                            status,
                            approval_token,
                            payload,
                        ),
                    )
                    row_id = int(cursor.lastrowid)
                except sqlite3.IntegrityError:
                    row = connection.execute(
                        "SELECT * FROM actions WHERE action_id=?", (action["action_id"],)
                    ).fetchone()
                    return self._decode_row(row)
                row = connection.execute("SELECT * FROM actions WHERE id=?", (row_id,)).fetchone()
                return self._decode_row(row)

        return self._execute_with_retry(operation)

    def latest_action(self) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM actions ORDER BY id DESC LIMIT 1").fetchone()
        return self._decode_row(row)

    def next_approved_action(self, after_row_id: int = 0) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM actions
                WHERE id > ? AND status='approved'
                ORDER BY id ASC LIMIT 1
                """,
                (int(after_row_id),),
            ).fetchone()
        return self._decode_row(row)

    def mark_action(self, row_id: int, status: str, applied_step: int | None = None) -> None:
        def operation() -> None:
            with self._connect() as connection:
                connection.execute(
                    "UPDATE actions SET status=?, applied_step=COALESCE(?, applied_step) WHERE id=?",
                    (status, applied_step, int(row_id)),
                )

        self._execute_with_retry(operation)

    def actions(self, limit: int = 100) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 5000))
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM actions ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [self._decode_row(row) for row in rows]

    def log_event(
        self,
        severity: str,
        source: str,
        message: str,
        payload: dict[str, Any] | None = None,
    ) -> int:
        def operation() -> int:
            with self._connect() as connection:
                cursor = connection.execute(
                    """
                    INSERT INTO events(created_at, severity, source, message, payload)
                    VALUES(?, ?, ?, ?, ?)
                    """,
                    (
                        utc_now_iso(),
                        severity.upper(),
                        source,
                        message,
                        json_dumps(payload) if payload is not None else None,
                    ),
                )
                return int(cursor.lastrowid)

        return self._execute_with_retry(operation)

    def events(self, limit: int = 100, severity: str | None = None) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 5000))
        query = "SELECT * FROM events"
        params: list[Any] = []
        if severity:
            query += " WHERE severity=?"
            params.append(severity.upper())
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        with self._connect() as connection:
            rows = connection.execute(query, params).fetchall()
        result = []
        for row in rows:
            value = dict(row)
            if value.get("payload"):
                try:
                    value["payload"] = json.loads(value["payload"])
                except json.JSONDecodeError:
                    pass
            result.append(value)
        return result

    def compare_latest(self) -> dict[str, Any]:
        baseline = self.latest_state("baseline")
        controlled = self.latest_state("controlled")
        if not baseline or not controlled:
            return {
                "ready": False,
                "message": "Both baseline and controlled simulations must publish at least one state.",
                "baseline": baseline,
                "controlled": controlled,
            }
        base_kwh = float(baseline.get("cumulative_kwh", 0.0))
        control_kwh = float(controlled.get("cumulative_kwh", 0.0))
        saving_pct = ((base_kwh - control_kwh) / base_kwh * 100.0) if base_kwh > 0 else 0.0
        base_peak = float(baseline.get("peak_kw", 0.0))
        control_peak = float(controlled.get("peak_kw", 0.0))
        peak_reduction_pct = ((base_peak - control_peak) / base_peak * 100.0) if base_peak > 0 else 0.0
        return {
            "ready": True,
            "baseline_cumulative_kwh": base_kwh,
            "controlled_cumulative_kwh": control_kwh,
            "energy_saving_pct": saving_pct,
            "baseline_peak_kw": base_peak,
            "controlled_peak_kw": control_peak,
            "peak_reduction_pct": peak_reduction_pct,
            "baseline_step": baseline.get("sim_step"),
            "controlled_step": controlled.get("sim_step"),
        }
