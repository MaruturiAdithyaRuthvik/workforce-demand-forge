# Workforce Demand Forecaster

Deterministic synthetic workforce planning data, source validation, rule-based anomaly detection, rule-based recommendations, and weekly demand forecasting. This is a command-line project, not a web application.

## Quickstart

1. Install Python 3.11+.
2. Run `uv sync --extra dev` (or `python -m pip install -e ".[dev]"`).
3. Generate data: `wdf generate --scale starter --seed 20261022 --out output/starter`.
4. Validate: `wdf validate --input output/starter`.
5. Run `wdf forecast --input output/starter`, `wdf detect --input output/starter`, or `wdf evaluate --input output/starter`.

The starter scale is 300 employees, 60 skills, and 30 projects. The full scale is 5,000 employees, 300 skills, and 500 projects. Output includes a CSV and JSON per table, schema/seed SQL, SQLite database, and a manifest. `uv.lock` pins the full dependency graph; `requirements-lock.txt` pins runtime and development tools.

## Layout

- `wdf/`: generator, validators, detectors, forecast, evaluation, and CLI.
- `config/`: fixed calendar, thresholds, and scale settings.
- `tests/`: deterministic and behavioral checks.
- `output/starter/`: committed starter sample output.

`2026` has 53 ISO weeks; W53 begins 2026-12-28. Weeks through W43 are history, and later weeks form the forecast horizon. See [DESIGN_DECISIONS.md](docs/DESIGN_DECISIONS.md), [ASSUMPTIONS.md](docs/ASSUMPTIONS.md), and [LIMITATIONS.md](docs/LIMITATIONS.md).

## Verification

Run `make test`, `make all`, and `make repro`. `wdf repro` compares repeated canonical exports and verifies that changing the seed changes hashes. The committed starter sample was generated and validated on Python 3.14.7, NumPy 2.3.3, and pandas 3.0.0.

## Verified starter run

These are real results from seed `20261022` (held-out seed `20261023`):

- Rows: 300 employees, 60 skills, 30 projects, 393 demand lines, 304 allocations, 15,900 availability rows, 15,900 utilization rows, 350 gap rows, and 253 gap actions.
- Validation: **PASS**, 0 errors; 7 approved demand duplicates and 6 injected skill currency mismatches were reported as expected anomaly findings.
- Detector P/R/F1: **1.000 / 1.000 / 1.000** for each of the four issue types on both seeds.
- Full-scale generation and validation: **66.73 seconds** on the local Windows/Python 3.14.7 environment.
- Reproducibility: **PASS**; 46 canonical CSV/JSON/SQL files and the logical SQLite dump matched for repeated seed `20261022`; seed `20261023` produced different hashes.

Rolling-origin forecast WAPE (lower is better; bias is signed relative error):

| Method | Horizon | WAPE | Bias |
|---|---:|---:|---:|
| 4-week moving average | 4 | 1.5708 | -0.1111 |
| 4-week moving average | 8 | 1.5192 | -0.1903 |
| 4-week moving average | 12 | 1.4605 | -0.2887 |
| Pipeline adjusted | 4 | 0.4391 | -0.4391 |
| Pipeline adjusted | 8 | 0.5650 | -0.5650 |
| Pipeline adjusted | 12 | 0.6747 | -0.6747 |

Forecast metrics and per-issue seed-specific scores are in [output/starter/metrics.json](output/starter/metrics.json); the row-level validation counts are in [output/starter/validation_report.json](output/starter/validation_report.json). The baseline comparison is reported honestly: pipeline adjustment was better at all three tested horizons for this synthetic sample.

## Data documentation

See [DATA_DICTIONARY.md](docs/DATA_DICTIONARY.md), [ERD.md](docs/ERD.md), and [TRACEABILITY.md](docs/TRACEABILITY.md).

## Environment and limitations

Python 3.11 or newer is required. Dependencies are pinned in `pyproject.toml`, `uv.lock`, and `requirements-lock.txt`. Full scale completed in 66.73 seconds in the recorded local run; runtime varies by machine. NumPy generator streams are only stable within a pinned version. All output is synthetic and should not be used for real workforce decisions.
