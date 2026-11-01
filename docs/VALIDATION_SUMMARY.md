# Validation and evaluation summary

The following results were collected from a real run using starter scale, main seed `20261022`, held-out seed `20261023`, Python 3.14.7, NumPy 2.3.3, and pandas 3.0.0.

## Data validation

**PASS** with 0 structural errors. The validator checked 53 weeks of employee capacity, 26 foreign-key relationships, lifecycle state history, identifiers, dates, and recomputed derived tables. Seven Approved demand business-key duplicates and six intentionally wrong skill currency flags were retained as injected data-quality cases and reported as warnings for the detector.

Selected row counts:

| Table | Rows |
|---|---:|
| Employees | 300 |
| Skills | 60 |
| Projects | 30 |
| EmployeeSkill | 2,198 |
| DemandLine | 393 |
| Allocation | 304 |
| Availability | 15,900 |
| Utilization | 15,900 |
| GapAnalysis | 350 |
| GapAction | 253 |
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
| 4-week moving average | 4 | 1.5708 | -0.1111 |
| 4-week moving average | 8 | 1.5192 | -0.1903 |
| 4-week moving average | 12 | 1.4605 | -0.2887 |
| Pipeline adjusted | 4 | 0.4391 | -0.4391 |
| Pipeline adjusted | 8 | 0.5650 | -0.5650 |
| Pipeline adjusted | 12 | 0.6747 | -0.6747 |

Pipeline adjustment has lower WAPE in this particular synthetic run. Both methods have negative bias; the moving average is especially weak on this dataset. No claim is made that this ranking generalizes.

## Reproducibility and scale

- Same-seed canonical files: **PASS**, 46 CSV/JSON/SQL files matched.
- Same-seed logical SQLite dump: **PASS**.
- Different-seed hashes: **PASS**, seed `20261023` differs from `20261022`.
- Full scale: **PASS**, generation and validation completed in 66.73 seconds on the recorded Windows/Python 3.14.7 environment.

Detailed artifacts: `output/starter/metrics.json`, `output/starter/validation_report.json`, and `output/repro_report.json`.
