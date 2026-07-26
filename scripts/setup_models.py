from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from core.config import settings
from energyplus.idf_parser import inspect_idf, prepare_demo_idf


IDF_CANDIDATES = (
    "5ZoneAirCooled.idf",
    "5ZoneVAV-Pri-SecLoop.idf",
    "ASHRAE9012016_SmallOffice_Denver.idf",
)


def find_idf(home: Path) -> Path:
    example_dir = home / "ExampleFiles"
    for name in IDF_CANDIDATES:
        candidate = example_dir / name
        if candidate.exists():
            return candidate
    for name in IDF_CANDIDATES:
        matches = list(home.rglob(name))
        if matches:
            return matches[0]
    raise FileNotFoundError(
        f"No suitable EnergyPlus example IDF was found below {home}. "
        "Supply one with --idf."
    )


def find_weather(home: Path) -> Path:
    weather_dir = home / "WeatherData"
    preferred_patterns = (
        "*Chicago*TMY3.epw",
        "*Chicago*.epw",
        "*Delhi*.epw",
        "*.epw",
    )
    for pattern in preferred_patterns:
        matches = list(weather_dir.glob(pattern)) if weather_dir.exists() else []
        if not matches:
            matches = list(home.rglob(pattern))
        if matches:
            return matches[0]
    raise FileNotFoundError(
        f"No EPW weather file was found below {home}. Supply one with --weather."
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare a short EnergyPlus demo model for EcoPilot.")
    parser.add_argument("--idf", type=Path, help="Optional source IDF from the installed EnergyPlus version.")
    parser.add_argument("--weather", type=Path, help="Optional EPW weather file.")
    parser.add_argument("--days", type=int, default=3, help="Demo RunPeriod length, from 1 to 28 days.")
    args = parser.parse_args()

    if settings.energyplus_home is None and (args.idf is None or args.weather is None):
        raise RuntimeError(
            "Set ENERGYPLUS_HOME in .env, or provide both --idf and --weather paths."
        )

    home = settings.energyplus_home or Path(".")
    source_idf = args.idf.resolve() if args.idf else find_idf(home)
    source_weather = args.weather.resolve() if args.weather else find_weather(home)
    if not source_idf.exists() or not source_weather.exists():
        raise FileNotFoundError("The selected IDF or weather file does not exist.")

    settings.baseline_idf.parent.mkdir(parents=True, exist_ok=True)
    prepare_demo_idf(source_idf, settings.baseline_idf, days=args.days)
    shutil.copy2(settings.baseline_idf, settings.controlled_idf)
    shutil.copy2(source_weather, settings.weather_file)

    info = inspect_idf(settings.controlled_idf)
    print(f"Source IDF: {source_idf}")
    print(f"Weather: {source_weather}")
    print(f"Baseline: {settings.baseline_idf}")
    print(f"Controlled: {settings.controlled_idf}")
    print(f"Zones found: {len(info.zones)}")
    print(f"Cooling schedules: {list(info.cooling_schedules)}")
    print(f"Heating schedules: {list(info.heating_schedules)}")
    print(f"Lighting schedules: {list(info.lighting_schedules)}")
    print(f"Ventilation schedules: {list(info.ventilation_schedules)}")
    if not info.cooling_schedules:
        print(
            "WARNING: No cooling thermostat schedules were discovered. Choose a different IDF or set "
            "CONTROLLED_COOLING_SCHEDULES in .env after inspecting exchange_points.json."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
