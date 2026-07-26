from __future__ import annotations

import argparse
import os
import sys
import uuid
from pathlib import Path

from core.config import settings
from core.storage import SQLiteStore
from energyplus.actuator_writer import ActuatorWriter
from energyplus.callbacks import SimulationCallbacks
from energyplus.handle_registry import HandleRegistry
from energyplus.idf_parser import inspect_idf
from energyplus.runtime_monitor import RuntimeMonitor
from energyplus.sensor_reader import SensorReader


def load_energyplus_api():
    energyplus_home = settings.energyplus_home
    if energyplus_home is None:
        raise RuntimeError("ENERGYPLUS_HOME is not set. Copy .env.example to .env and set the installation path.")
    if not energyplus_home.exists():
        raise RuntimeError(f"ENERGYPLUS_HOME does not exist: {energyplus_home}")
    sys.path.insert(0, str(energyplus_home))
    try:
        from pyenergyplus.api import EnergyPlusAPI
    except ImportError as exc:
        raise RuntimeError(
            f"Could not import pyenergyplus from {energyplus_home}. Verify the EnergyPlus installation path."
        ) from exc
    return EnergyPlusAPI


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run an EnergyPlus baseline or EcoPilot-controlled twin.")
    parser.add_argument("--mode", choices=["baseline", "controlled"], required=True)
    parser.add_argument("--idf", type=Path)
    parser.add_argument("--weather", type=Path, default=settings.weather_file)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--realtime-delay", type=float, default=0.05)
    parser.add_argument("--quiet", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    idf_path = args.idf or (settings.baseline_idf if args.mode == "baseline" else settings.controlled_idf)
    output_dir = args.output or settings.project_root / "data" / args.mode / "energyplus-output"
    output_dir.mkdir(parents=True, exist_ok=True)
    run_id = args.run_id or f"{args.mode}-{uuid.uuid4()}"

    for required_path, label in ((idf_path, "IDF"), (args.weather, "weather file")):
        if not required_path.exists():
            raise FileNotFoundError(
                f"Missing {label}: {required_path}. Run `python scripts/setup_models.py` first."
            )

    EnergyPlusAPI = load_energyplus_api()
    api = EnergyPlusAPI()
    state = api.state_manager.new_state()
    store = SQLiteStore(settings.db_path)
    model_info = inspect_idf(idf_path)
    registry = HandleRegistry(api, model_info, args.mode)
    registry.request_variables(state)
    reader = SensorReader(api, registry, run_id, args.mode)
    writer = ActuatorWriter(api, registry)
    monitor = RuntimeMonitor(
        store,
        args.mode,
        settings.live_dir / f"{args.mode}_energyplus.log",
    )
    callbacks = SimulationCallbacks(
        api=api,
        store=store,
        registry=registry,
        reader=reader,
        writer=writer,
        monitor=monitor,
        mode=args.mode,
        realtime_delay=args.realtime_delay,
    )

    api.runtime.callback_begin_zone_timestep_before_init_heat_balance(
        state, callbacks.before_zone_timestep
    )
    api.runtime.callback_end_zone_timestep_after_zone_reporting(
        state, callbacks.after_zone_timestep
    )
    api.runtime.callback_message(state, monitor.on_message)
    api.runtime.callback_progress(state, monitor.on_progress)
    api.runtime.set_console_output_status(state, not args.quiet)

    store.log_event(
        "INFO",
        f"energyplus:{args.mode}",
        "Simulation started.",
        {"run_id": run_id, "idf": str(idf_path), "weather": str(args.weather)},
    )
    exit_code = api.runtime.run_energyplus(
        state,
        ["-d", str(output_dir), "-w", str(args.weather), str(idf_path)],
    )
    store.log_event(
        "INFO" if exit_code == 0 else "ERROR",
        f"energyplus:{args.mode}",
        f"Simulation finished with exit code {exit_code}.",
        monitor.summary(),
    )
    api.state_manager.delete_state(state)
    return int(exit_code)


if __name__ == "__main__":
    raise SystemExit(main())
