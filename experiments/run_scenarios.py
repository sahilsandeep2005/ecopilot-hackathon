from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from core.config import settings
from core.storage import SQLiteStore
from experiments.generate_report import create_markdown_report


def _process(command: list[str], log_path: Path) -> subprocess.Popen:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_file = log_path.open("w", encoding="utf-8")
    return subprocess.Popen(
        command,
        cwd=settings.project_root,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        text=True,
    )


def _terminate(process: subprocess.Popen | None) -> None:
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=8)
    except subprocess.TimeoutExpired:
        process.kill()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Launch baseline, controlled, MCP, and agent processes.")
    parser.add_argument("--realtime-delay", type=float, default=0.05)
    parser.add_argument("--deterministic-agent", action="store_true")
    parser.add_argument("--keep-database", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    missing = [path for path in (settings.baseline_idf, settings.controlled_idf, settings.weather_file) if not path.exists()]
    if missing:
        raise FileNotFoundError(
            "Missing model files: " + ", ".join(str(path) for path in missing) + ". Run scripts/setup_models.py."
        )

    store = SQLiteStore(settings.db_path)
    if not args.keep_database:
        store.clear_runtime_data()

    python = sys.executable
    logs = settings.live_dir
    mcp_process = agent_process = baseline_process = controlled_process = None
    try:
        mcp_process = _process([python, "-m", "mcp_server.server"], logs / "mcp_server.log")
        time.sleep(2.0)
        agent_command = [python, "-m", "agent.orchestrator"]
        if args.deterministic_agent:
            agent_command.append("--deterministic")
        agent_process = _process(agent_command, logs / "agent.log")

        baseline_process = _process(
            [
                python,
                "-m",
                "energyplus.runner",
                "--mode",
                "baseline",
                "--realtime-delay",
                str(args.realtime_delay),
                "--quiet",
            ],
            logs / "baseline_runner.log",
        )
        controlled_process = _process(
            [
                python,
                "-m",
                "energyplus.runner",
                "--mode",
                "controlled",
                "--realtime-delay",
                str(args.realtime_delay),
                "--quiet",
            ],
            logs / "controlled_runner.log",
        )

        baseline_code = baseline_process.wait()
        controlled_code = controlled_process.wait()
        report = create_markdown_report(settings.project_root / "data" / "ecopilot-report.md", store)
        print(f"Baseline exit code: {baseline_code}")
        print(f"Controlled exit code: {controlled_code}")
        print(f"Report: {report}")
        return 0 if baseline_code == 0 and controlled_code == 0 else 1
    finally:
        _terminate(agent_process)
        _terminate(mcp_process)
        _terminate(baseline_process)
        _terminate(controlled_process)


if __name__ == "__main__":
    raise SystemExit(main())
