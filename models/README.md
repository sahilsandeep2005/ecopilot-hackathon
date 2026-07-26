# Building model files

Do not hand-create `baseline.idf`, `controlled.idf`, or `weather.epw` here.
They must match the installed EnergyPlus version.

Run:

```bash
python scripts/setup_models.py --days 3
```

The script copies an installed EnergyPlus example model, shortens its weather-file
RunPeriod for a live demonstration, and creates two identical twins. Runtime API
actuation—not permanent IDF differences—creates the controlled case.

For the final submission, replace the example with the chosen reference building,
retain an unmodified copy, and document every IDF change.
