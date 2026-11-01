# Workforce Demand Forecaster

Deterministic synthetic workforce planning data, source validation, rule-based anomaly detection, rule-based recommendations, and weekly demand forecasting. This is a command-line project, not a web application.

## Quickstart

1. Install Python 3.11+.
2. Run `uv sync --locked` (this installs the default development dependency group used by `make test`).
3. Generate data: `uv run wdf generate --scale starter --seed 20261022 --out output/starter`.
4. Validate: `uv run wdf validate --input output/starter`.
5. Run `uv run wdf forecast --input output/starter`, `uv run wdf detect --input output/starter`, or `uv run wdf evaluate --input output/starter`.

The starter scale is 300 employees, 60 skills, and 30 projects. The full scale is 5,000 employees, 300 skills, and 500 projects. Output includes a CSV and JSON per table, schema/seed SQL, SQLite database, and a manifest. `uv.lock` pins the full dependency graph; `requirements-lock.txt` pins runtime and development tools.

## Layout

- `wdf/`: generator, validators, detectors, forecast, evaluation, and CLI.
- `config/`: fixed calendar, thresholds, and scale settings.
- `tests/`: deterministic and behavioral checks.
- `output/starter/`: committed starter sample output.

`2026` has 53 ISO weeks; W53 begins 2026-12-28. Weeks through W43 are history, and later weeks form the forecast horizon. See [DESIGN_DECISIONS.md](docs/DESIGN_DECISIONS.md), [ASSUMPTIONS.md](docs/ASSUMPTIONS.md), and [LIMITATIONS.md](docs/LIMITATIONS.md).

## Verification

Run `uv run pytest`, `uv run wdf validate --input output/starter`, and `uv run wdf repro --scale starter --seed 20261022 --out output/starter-repro`. `wdf repro` compares repeated canonical exports and verifies that changing the seed changes hashes. GNU Make targets are also provided, but Make is not installed in the audited Windows environment.

## Verified starter run

These are real results from seed `20261022` (held-out seed `20261023`):

- Rows: 300 employees, 60 skills, 30 projects, 393 demand lines, 305 allocations, 15,900 availability rows, 15,900 utilization rows, 350 gap rows, and 244 gap actions.
- Validation: **PASS**, 0 errors; 7 approved demand duplicates and 6 injected skill currency mismatches were reported as expected anomaly findings.
- Detector P/R/F1: **1.000 / 1.000 / 1.000** for each of the four issue types on both seeds.
- Full-scale generation and validation: **70.50 seconds**, with a sampled process-tree peak working set of **720.1 MiB** on the local Windows/Python 3.14.7 environment.
- Reproducibility: **PASS**; 46 canonical CSV/JSON/SQL files and the logical SQLite dump matched for repeated seed `20261022`; seed `20261023` produced different hashes.

Rolling-origin forecast WAPE (lower is better; bias is signed relative error):

| Method | Horizon | WAPE | Bias |
|---|---:|---:|---:|
| 4-week moving average | 4 | 1.5723 | -0.1085 |
| 4-week moving average | 8 | 1.5266 | -0.1795 |
| 4-week moving average | 12 | 1.4682 | -0.2786 |
| Pipeline adjusted | 4 | 0.4303 | -0.4303 |
| Pipeline adjusted | 8 | 0.5586 | -0.5586 |
| Pipeline adjusted | 12 | 0.6711 | -0.6711 |

Forecast metrics and per-issue seed-specific scores are in [output/starter/metrics.json](output/starter/metrics.json); the row-level validation counts are in [output/starter/validation_report.json](output/starter/validation_report.json). On this starter sample, pipeline adjustment wins WAPE at all three horizons but is more negatively biased at each horizon. The full-scale result differs: moving average wins WAPE at 12 weeks.

## Data documentation

See [DATA_DICTIONARY.md](docs/DATA_DICTIONARY.md), [ERD.md](docs/ERD.md), and [TRACEABILITY.md](docs/TRACEABILITY.md).

## Environment and limitations

Python 3.11 or newer is required. Dependencies are pinned in `pyproject.toml`, `uv.lock`, and `requirements-lock.txt`. Full scale completed in 70.50 seconds with a sampled 720.1 MiB process-tree peak in the recorded local run; runtime and memory vary by machine. NumPy generator streams are only stable within a pinned version. All output is synthetic and should not be used for real workforce decisions.
