# Workforce Demand Forecaster

Deterministic synthetic workforce planning data, source validation, rule-based anomaly detection, rule-based recommendations, and weekly demand forecasting. This is a command-line project, not a web application.

## Quickstart

1. Install Python 3.11+.
2. Run `uv sync --locked` (this installs the default development dependency group used by `make test`).
3. Generate data: `uv run wdf generate --scale starter --seed 20261022 --out output/starter`.
4. Validate: `uv run wdf validate --input output/starter`.
5. Run `uv run wdf forecast --input output/starter`, `uv run wdf detect --input output/starter`, or `uv run wdf evaluate --input output/starter`.

The starter scale is 300 employees, 60 skills, and 30 projects. The full scale is 5,000 employees, 300 skills, and 500 projects. Output includes a CSV and JSON per table, role-level `forecast.csv`, project/role/week `forecast_project.csv`, schema/seed SQL, SQLite database, and a manifest. Project forecasts use only demand visible at each origin and reconcile to the role-level totals. Utilization is classified into config-driven risk bands, including a legal 0.9–1.0 high-utilization band with traceable review actions that are distinct from anomaly detection. `uv.lock` pins the full dependency graph; `requirements-lock.txt` pins runtime and development tools.

## Layout

- `wdf/`: generator, validators, detectors, forecast, evaluation, and CLI.
- `config/`: fixed calendar, generation distributions and rates, work hours, thresholds, and scale settings.
- `tests/`: deterministic and behavioral checks.
- `output/starter/`: committed starter sample output.

`2026` has 53 ISO weeks; W53 begins 2026-12-28. Weeks through W43 are history, and later weeks form the forecast horizon. See [DESIGN_DECISIONS.md](docs/DESIGN_DECISIONS.md), [ASSUMPTIONS.md](docs/ASSUMPTIONS.md), and [LIMITATIONS.md](docs/LIMITATIONS.md).

## Verification

Run `uv run pytest --cov=wdf --cov-report=term-missing`, `uv run wdf validate --input output/starter`, and `uv run wdf repro --scale starter --seed 20261022 --out output/starter-repro`. `wdf repro` compares repeated canonical exports and verifies that changing the seed changes hashes. GNU Make targets are also provided, but Make is not installed in the audited Windows environment.

## Verified starter run

These are real results from seed `20261022` (held-out seed `20261023`):

- Rows: 300 employees, 60 skills, 30 projects, 567 demand lines, 457 allocations, 15,900 availability rows, 15,900 utilization rows, 514 gap rows, and 579 gap actions.
- Validation: **PASS**, 0 errors; 11 approved demand duplicates and 6 injected skill currency mismatches were reported as expected anomaly findings.
- Exact starter validation warnings: `11 approved demand business-key duplicate(s), surfaced for anomaly detection`; `6 employee skill currency flag(s) disagree with expiry and are detector cases`. These are intentional injected anomaly fixtures (duplicate Approved demand and stale-skill/current-flag mismatch), not structural validation failures.
- Detector P/R/F1: **1.000 / 1.000 / 1.000** for each of the four issue types on both seeds.
- Full-scale generation and validation: **101.609 seconds**, with a sampled process-tree peak working set of **827.4 MiB** on the local Windows/Python 3.14.7 environment.
- Reproducibility: **PASS**; 47 canonical CSV/JSON/SQL files and the logical SQLite dump matched for repeated seed `20261022`; seed `20261023` changed 40 file hashes.

Starter rolling-origin backtest (36/32/28 origins for 4/8/12 weeks; WAPE lower is better, bias is signed relative error):

| Method | Horizon | WAPE | Bias |
|---|---:|---:|---:|
| 4-week moving average | 4 | 1.54722625 | -0.02871761 |
| 4-week moving average | 8 | 1.53629666 | -0.04952360 |
| 4-week moving average | 12 | 1.51146390 | -0.06915606 |
| Pipeline adjusted | 4 | 0.38732809 | -0.38732809 |
| Pipeline adjusted | 8 | 0.52632881 | -0.52632881 |
| Pipeline adjusted | 12 | 0.63408723 | -0.63408723 |
| Pipeline realization adjusted | 4 | 0.38518927 | -0.03346620 |
| Pipeline realization adjusted | 8 | 0.49365089 | -0.25614278 |
| Pipeline realization adjusted | 12 | 0.59857961 | -0.43066711 |

Forecast metrics and per-issue seed-specific scores are in [output/starter/metrics.json](output/starter/metrics.json); the row-level validation counts are in [output/starter/validation_report.json](output/starter/validation_report.json). On this starter sample, pipeline realization adjustment wins WAPE at all three horizons; it remains negatively biased. In the full-scale backtest it also wins WAPE at all horizons, but underforecasts at 8 and 12 weeks. These are synthetic-data results, not a general forecast benchmark.

Starter project/role/week backtest (same rolling origins; WAPE lower is better):

| Method | Horizon | WAPE | Bias |
|---|---:|---:|---:|
| 4-week moving average | 4 | 1.92469908 | -0.02872118 |
| 4-week moving average | 8 | 1.91321131 | -0.04952759 |
| 4-week moving average | 12 | 1.89696901 | -0.06915782 |
| Pipeline adjusted | 4 | 0.38732895 | -0.38732895 |
| Pipeline adjusted | 8 | 0.52632965 | -0.52632965 |
| Pipeline adjusted | 12 | 0.63408772 | -0.63408772 |
| Pipeline realization adjusted | 4 | 0.41179253 | -0.03346475 |
| Pipeline realization adjusted | 8 | 0.52216769 | -0.25614225 |
| Pipeline realization adjusted | 12 | 0.62142750 | -0.43066720 |

Project-level WAPE is higher for the moving-average method because demand must be assigned to projects from their historical role mix. The realization-adjusted pipeline has lower project-level WAPE at 4 and 8 weeks than at 12 weeks; the role-level and project-level method winners need not be the same.

Full-scale project/role/week backtest (36/32/28 origins):

| Method | Horizon | WAPE | Bias |
|---|---:|---:|---:|
| 4-week moving average | 4 | 1.85634063 | -0.11000170 |
| 4-week moving average | 8 | 1.80812723 | -0.16911561 |
| 4-week moving average | 12 | 1.75412930 | -0.22819106 |
| Pipeline adjusted | 4 | 0.37434853 | -0.37434853 |
| Pipeline adjusted | 8 | 0.52768210 | -0.52768210 |
| Pipeline adjusted | 12 | 0.65303907 | -0.65303907 |
| Pipeline realization adjusted | 4 | 0.38780579 | 0.00672645 |
| Pipeline realization adjusted | 8 | 0.49934238 | -0.24277502 |
| Pipeline realization adjusted | 12 | 0.61643032 | -0.44600495 |

## Data documentation

See [DATA_DICTIONARY.md](docs/DATA_DICTIONARY.md), [ERD.md](docs/ERD.md), and [TRACEABILITY.md](docs/TRACEABILITY.md).

## Environment and limitations

Python 3.11 or newer is required. Dependencies are pinned in `pyproject.toml`, `uv.lock`, and `requirements-lock.txt`. Full-scale runtime and memory vary by machine; see the verified run above for the current audit measurement. NumPy generator streams are only stable within a pinned version. All output is synthetic and should not be used for real workforce decisions.
