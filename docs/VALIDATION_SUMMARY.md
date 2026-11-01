# Validation and evaluation summary

The following results were collected from fresh starter and full runs using main seed `20261022`, held-out seed `20261023`, Python 3.14.7, NumPy 2.3.3, and pandas 3.0.0.

## Data validation

**PASS** with 0 structural errors. The validator checked 53 weeks of employee capacity, 26 foreign-key relationships, lifecycle state history, identifiers, dates, and recomputed derived tables. Seven Approved demand business-key duplicates and six intentionally wrong skill currency flags were retained as injected data-quality cases and reported as warnings for the detector.

Selected row counts:

| Table | Rows |
|---|---:|
| Employees | 300 |
| Skills | 60 |
| Projects | 30 |
| EmployeeSkill | 2,127 |
| DemandLine | 393 |
| Allocation | 305 |
| Availability | 15,900 |
| Utilization | 15,900 |
| GapAnalysis | 350 |
| GapAction | 244 |
| Training | 16 |

## Detection evaluation

Metrics are evaluated by exact source `record_id` and issue type. Every issue family met the 0.95 target on both seeds:

| Issue type | Main P | Main R | Main F1 | Held-out P | Held-out R | Held-out F1 |
|---|---:|---:|---:|---:|---:|---:|
| ALLOC_EXCEEDS_AVAILABILITY | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| STALE_SKILL_TREATED_CURRENT | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| DEMAND_DOUBLE_COUNTED | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| OVERLAPPING_PROJECT_ASSIGNMENT | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |

## Forecast backtest

| Method | Horizon (weeks) | WAPE | Bias |
|---|---:|---:|---:|
| 4-week moving average | 4 | 1.5723 | -0.1085 |
| 4-week moving average | 8 | 1.5266 | -0.1795 |
| 4-week moving average | 12 | 1.4682 | -0.2786 |
| Pipeline adjusted | 4 | 0.4303 | -0.4303 |
| Pipeline adjusted | 8 | 0.5586 | -0.5586 |
| Pipeline adjusted | 12 | 0.6711 | -0.6711 |

On the starter sample, pipeline adjustment has lower WAPE at all three horizons. Both methods underforecast; pipeline adjustment's bias is more negative at every horizon. No claim is made that this ranking generalizes.

The full-scale backtest produced a different 12-week ranking:

| Method | Horizon (weeks) | WAPE | Bias |
|---|---:|---:|---:|
| 4-week moving average | 4 | 0.5451 | -0.0949 |
| 4-week moving average | 8 | 0.5566 | -0.1532 |
| 4-week moving average | 12 | 0.5629 | -0.2220 |
| Pipeline adjusted | 4 | 0.3766 | -0.3766 |
| Pipeline adjusted | 8 | 0.5264 | -0.5264 |
| Pipeline adjusted | 12 | 0.6498 | -0.6498 |

Pipeline adjustment wins at 4 and 8 weeks; moving average wins at 12. Pipeline adjustment is more negatively biased at each horizon.

## Reproducibility and scale

- Same-seed canonical files: **PASS**, 46 CSV/JSON/SQL files matched.
- Same-seed logical SQLite dump: **PASS**.
- Different-seed hashes: **PASS**, seed `20261023` differs from `20261022`.
- Full scale: **PASS**, generation and validation completed in 70.50 seconds with sampled process-tree peak working set 720.1 MiB on the recorded Windows/Python 3.14.7 environment.
- Full-scale rows: 5,000 employees; 300 skills; 500 projects; 57,595 employee skills; 6,193 demand lines; 5,025 allocations; 265,000 availability and utilization rows; 4,316 gaps; 1,939 gap actions.

Detailed artifacts: `output/starter/metrics.json`, `output/starter/validation_report.json`, and `output/repro_report.json`.
