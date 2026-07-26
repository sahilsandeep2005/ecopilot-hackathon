from pathlib import Path

from energyplus.idf_parser import inspect_idf, parse_idf, prepare_demo_idf


SAMPLE = """
Version, 26.2;
Timestep, 6;
SimulationControl, Yes, Yes, Yes, Yes, Yes;
RunPeriod, Demo, 1, 1, , 12, 31, ;
Zone, Core Zone;
Schedule:Constant, Cool Schedule, Temperature, 24;
Schedule:Constant, Heat Schedule, Temperature, 20;
Schedule:Constant, Lights Schedule, Fraction, 1;
ThermostatSetpoint:DualSetpoint, Dual, Heat Schedule, Cool Schedule;
Lights, Lights, Core Zone, Lights Schedule, Watts/Area, , 10;
People, People, Core Zone, Occupancy, People, 5;
"""


def test_parser_discovers_controls(tmp_path: Path):
    path = tmp_path / "sample.idf"
    path.write_text(SAMPLE)
    info = inspect_idf(path)
    assert info.zones == ["Core Zone"]
    assert "Cool Schedule" in info.cooling_schedules
    assert "Heat Schedule" in info.heating_schedules
    assert "Lights Schedule" in info.lighting_schedules


def test_demo_preparation_shortens_runperiod(tmp_path: Path):
    source = tmp_path / "source.idf"
    destination = tmp_path / "demo.idf"
    source.write_text(SAMPLE)
    prepare_demo_idf(source, destination, days=3)
    objects = parse_idf(destination)
    run_period = next(fields for fields in objects if fields[0].upper() == "RUNPERIOD")
    assert run_period[5] == "1"
    assert run_period[6] == "3"
