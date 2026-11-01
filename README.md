# Workforce Demand Forecaster

Deterministic synthetic workforce planning data, source validation, rule-based anomaly detection, rule-based recommendations, and weekly demand forecasting. This is a command-line project, not a web application.

## Quickstart

1. Install Python 3.11+.
2. Run `python -m pip install -e ".[dev]"`.
3. Generate data: `wdf generate --scale starter --seed 20261022 --out output/starter`.
4. Validate: `wdf validate --input output/starter`.
5. Run `wdf forecast --input output/starter`, `wdf detect --input output/starter`, or `wdf evaluate --input output/starter`.

The starter scale is 300 employees, 60 skills, and 30 projects. The full scale is 5,000 employees, 300 skills, and 500 projects. Output includes a CSV and JSON per table, schema/seed SQL, SQLite database, and a manifest.

## Layout

- `wdf/`: generator, validators, detectors, forecast, evaluation, and CLI.
- `config/`: fixed calendar, thresholds, and scale settings.
- `tests/`: deterministic and behavioral checks.
- `output/starter/`: committed starter sample output.

`2026` has 53 ISO weeks; W53 begins 2026-12-28. Weeks through W43 are history, and later weeks form the forecast horizon. See [DESIGN_DECISIONS.md](docs/DESIGN_DECISIONS.md), [ASSUMPTIONS.md](docs/ASSUMPTIONS.md), and [LIMITATIONS.md](docs/LIMITATIONS.md).

## Verification

Run `make test`, `make all`, and `make repro`. `wdf repro` compares repeated canonical exports and verifies that changing the seed changes hashes. Metrics in this document are populated after a real run.

## Data documentation

See [DATA_DICTIONARY.md](docs/DATA_DICTIONARY.md), [ERD.md](docs/ERD.md), and [TRACEABILITY.md](docs/TRACEABILITY.md).

## Environment and limitations

Python 3.11 or newer is required. Dependencies are pinned in `pyproject.toml` and `requirements-lock.txt`. Full scale is intended to run in under two minutes on a typical developer machine; measure on the target environment. NumPy generator streams are only stable within a pinned version. All output is synthetic and should not be used for real workforce decisions.
