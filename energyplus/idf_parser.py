from __future__ import annotations

import csv
import io
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable

from core.config import settings


def _remove_comments(text: str) -> str:
    lines: list[str] = []
    for line in text.splitlines():
        in_quote = False
        result: list[str] = []
        for char in line:
            if char == '"':
                in_quote = not in_quote
            if char == "!" and not in_quote:
                break
            result.append(char)
        lines.append("".join(result))
    return "\n".join(lines)


def _split_objects(text: str) -> list[str]:
    objects: list[str] = []
    buffer: list[str] = []
    in_quote = False
    for char in text:
        if char == '"':
            in_quote = not in_quote
        if char == ";" and not in_quote:
            value = "".join(buffer).strip()
            if value:
                objects.append(value)
            buffer = []
        else:
            buffer.append(char)
    return objects


def _split_fields(raw_object: str) -> list[str]:
    reader = csv.reader([raw_object.replace("\r", " ").replace("\n", " ")], skipinitialspace=True)
    values = next(reader, [])
    return [value.strip().strip('"') for value in values]


def parse_idf(path: Path | str) -> list[list[str]]:
    text = Path(path).read_text(encoding="utf-8", errors="ignore")
    clean = _remove_comments(text)
    return [fields for raw in _split_objects(clean) if (fields := _split_fields(raw))]


def write_idf(objects: Iterable[list[str]], path: Path | str) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for fields in objects:
        if not fields:
            continue
        lines.append(f"{fields[0]},")
        for index, field_value in enumerate(fields[1:], start=1):
            suffix = ";" if index == len(fields) - 1 else ","
            lines.append(f"  {field_value}{suffix}")
        lines.append("")
    destination.write_text("\n".join(lines), encoding="utf-8")


@dataclass
class IDFModelInfo:
    path: str
    zones: list[str] = field(default_factory=list)
    people_to_zone: dict[str, str] = field(default_factory=dict)
    cooling_schedules: dict[str, str] = field(default_factory=dict)
    heating_schedules: dict[str, str] = field(default_factory=dict)
    lighting_schedules: dict[str, str] = field(default_factory=dict)
    ventilation_schedules: dict[str, str] = field(default_factory=dict)
    all_schedule_types: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def inspect_idf(path: Path | str) -> IDFModelInfo:
    objects = parse_idf(path)
    info = IDFModelInfo(path=str(Path(path).resolve()))

    schedule_types: dict[str, str] = {}
    for fields in objects:
        object_type = fields[0].upper()
        if object_type.startswith("SCHEDULE:") and len(fields) > 1:
            schedule_types[fields[1]] = fields[0]
    info.all_schedule_types = schedule_types

    for fields in objects:
        object_type = fields[0].upper()
        if object_type == "ZONE" and len(fields) > 1:
            info.zones.append(fields[1])
        elif object_type == "PEOPLE" and len(fields) > 2:
            info.people_to_zone[fields[1]] = fields[2]
        elif object_type == "THERMOSTATSETPOINT:DUALSETPOINT" and len(fields) > 3:
            heating_schedule, cooling_schedule = fields[2], fields[3]
            if heating_schedule:
                info.heating_schedules[heating_schedule] = schedule_types.get(heating_schedule, "Schedule:Compact")
            if cooling_schedule:
                info.cooling_schedules[cooling_schedule] = schedule_types.get(cooling_schedule, "Schedule:Compact")
        elif object_type == "THERMOSTATSETPOINT:SINGLEHEATING" and len(fields) > 2:
            schedule = fields[2]
            info.heating_schedules[schedule] = schedule_types.get(schedule, "Schedule:Compact")
        elif object_type == "THERMOSTATSETPOINT:SINGLECOOLING" and len(fields) > 2:
            schedule = fields[2]
            info.cooling_schedules[schedule] = schedule_types.get(schedule, "Schedule:Compact")
        elif object_type == "LIGHTS" and len(fields) > 3:
            schedule = fields[3]
            if schedule:
                info.lighting_schedules[schedule] = schedule_types.get(schedule, "Schedule:Compact")

    ventilation_keywords = ("VENT", "MIN OA", "MINOA", "OUTDOOR AIR", "FRESH AIR", "OA SCHED")
    for schedule_name, schedule_type in schedule_types.items():
        upper_name = schedule_name.upper()
        if any(keyword in upper_name for keyword in ventilation_keywords):
            info.ventilation_schedules[schedule_name] = schedule_type

    def merge_overrides(target: dict[str, str], overrides: tuple[str, ...]) -> None:
        for name in overrides:
            target[name] = schedule_types.get(name, "Schedule:Compact")

    merge_overrides(info.cooling_schedules, settings.controlled_cooling_schedules)
    merge_overrides(info.heating_schedules, settings.controlled_heating_schedules)
    merge_overrides(info.lighting_schedules, settings.controlled_lighting_schedules)
    merge_overrides(info.ventilation_schedules, settings.controlled_ventilation_schedules)

    info.zones = list(dict.fromkeys(info.zones))
    return info


def enable_co2_simulation(objects: list[list[str]]) -> None:
    """Enable EnergyPlus zone CO2 calculations and timestep output."""
    outdoor_schedule_name = "EcoPilot Outdoor CO2"

    schedule_exists = any(
        len(fields) > 1
        and fields[0].upper().startswith("SCHEDULE:")
        and fields[1].upper() == outdoor_schedule_name.upper()
        for fields in objects
    )
    if not schedule_exists:
        objects.append(["Schedule:Constant", outdoor_schedule_name, "", "400"])

    contaminant_balance = next(
        (fields for fields in objects if fields and fields[0].upper() == "ZONEAIRCONTAMINANTBALANCE"),
        None,
    )
    if contaminant_balance is None:
        objects.append(
            [
                "ZoneAirContaminantBalance",
                "Yes",
                outdoor_schedule_name,
                "No",
                "",
            ]
        )
    else:
        while len(contaminant_balance) < 5:
            contaminant_balance.append("")
        contaminant_balance[1] = "Yes"
        contaminant_balance[2] = outdoor_schedule_name

    output_exists = any(
        len(fields) > 2
        and fields[0].upper() == "OUTPUT:VARIABLE"
        and fields[2].upper() == "ZONE AIR CO2 CONCENTRATION"
        for fields in objects
    )
    if not output_exists:
        objects.append(["Output:Variable", "*", "Zone Air CO2 Concentration", "Timestep"])


def prepare_demo_idf(source: Path | str, destination: Path | str, days: int = 3) -> None:
    objects = parse_idf(source)
    has_run_period = False
    for fields in objects:
        object_type = fields[0].upper()
        if object_type == "RUNPERIOD":
            has_run_period = True
            while len(fields) < 8:
                fields.append("")
            demo_days = max(1, min(days, 14))
            fields[2] = "7"                       # Start month: July
            fields[3] = "15"                      # Start day
            fields[4] = ""
            fields[5] = "7"                       # End month: July
            fields[6] = str(14 + demo_days)
            fields[7] = ""
        elif object_type == "TIMESTEP":
            if len(fields) == 1:
                fields.append("4")
            else:
                fields[1] = "4"
        elif object_type == "SIMULATIONCONTROL":
            while len(fields) < 6:
                fields.append("")
            fields[4] = "No"
            fields[5] = "Yes"

    if not has_run_period:
        demo_days = max(1, min(days, 14))
        objects.append([
            "RunPeriod",
            "EcoPilot Demo",
            "7",                       # Begin month
            "15",                      # Begin day
            "",
            "7",                       # End month
            str(14 + demo_days),       # End day
            "",
            "Monday",
            "Yes",
            "Yes",
            "No",
            "Yes",
            "Yes",
        ])

    enable_co2_simulation(objects)
    write_idf(objects, destination)
