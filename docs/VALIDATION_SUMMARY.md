# Validation and evaluation summary

Results below use seed `20261022`, held-out seeds `20261023` and `20261024` where indicated, and Python 3.14.7 / NumPy 2.3.3 / pandas 3.0.0.

## Data validation

Both generated scales passed validation with zero structural errors. The two warnings per scale are the intentionally injected Approved-demand duplicate groups and EmployeeSkill currency/expiry mismatches.

| Table | Starter rows | Full rows |
|---|---:|---:|
| Employees | 300 | 5,000 |
| Skills | 60 | 300 |
| Projects | 30 | 500 |
| EmployeeSkill | 2,127 | 57,595 |
| DemandPlan | 346 | 4,079 |
| DemandLine | 567 | 6,277 |
| Leave | 721 | 12,001 |
| Allocation | 457 | 7,535 |
| Availability | 15,900 | 265,000 |
| Utilization | 15,900 | 265,000 |
| GapAnalysis | 514 | 4,389 |
| GapAction | 325 | 2,151 |

The full independent stdlib checker passed PK/FK/enums/IDs/dates, 53-week capacity reconciliation, 265,000 utilization rows, 1,000 stratified gap recomputations, lifecycle state, injected duplicate-label agreement, and a fresh SQLite `PRAGMA foreign_key_check`.

## Detection evaluation

Full-scale exact source-record/issue-type metrics:

| Seed | Issue type | Injected / detected | TP | FP | FN | Precision | Recall | F1 |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 20261022 | ALLOC_EXCEEDS_AVAILABILITY | 79 / 79 | 79 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| 20261022 | DEMAND_DOUBLE_COUNTED | 121 / 121 | 121 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| 20261022 | OVERLAPPING_PROJECT_ASSIGNMENT | 31 / 31 | 31 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| 20261022 | STALE_SKILL_TREATED_CURRENT | 173 / 173 | 173 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| 20261023 | ALLOC_EXCEEDS_AVAILABILITY | 80 / 80 | 80 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| 20261023 | DEMAND_DOUBLE_COUNTED | 122 / 122 | 122 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| 20261023 | OVERLAPPING_PROJECT_ASSIGNMENT | 30 / 30 | 30 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| 20261023 | STALE_SKILL_TREATED_CURRENT | 168 / 168 | 168 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| 20261024 | ALLOC_EXCEEDS_AVAILABILITY | 82 / 82 | 82 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| 20261024 | DEMAND_DOUBLE_COUNTED | 126 / 126 | 126 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| 20261024 | OVERLAPPING_PROJECT_ASSIGNMENT | 28 / 28 | 28 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| 20261024 | STALE_SKILL_TREATED_CURRENT | 181 / 181 | 181 | 0 | 0 | 1.000 | 1.000 | 1.000 |

These are synthetic-rule results: injected records deliberately satisfy the detector predicates. No ground-truth labels or injected-ID lists appear in input-table fields, and source-only detection passes after deleting the `ground_truth` directory.

## Forecast backtests

Rolling-origin backtests use 36, 32, and 28 origins at the 4-, 8-, and 12-week horizons. WAPE is lower-is-better; bias is signed relative error.

### Starter

| Method | Horizon (weeks) | WAPE | Bias |
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

### Full

| Method | Horizon (weeks) | WAPE | Bias |
|---|---:|---:|---:|
| 4-week moving average | 4 | 0.57811463 | -0.11000130 |
| 4-week moving average | 8 | 0.56952677 | -0.16911512 |
| 4-week moving average | 12 | 0.57377841 | -0.22819074 |
| Pipeline adjusted | 4 | 0.37434853 | -0.37434853 |
| Pipeline adjusted | 8 | 0.52768210 | -0.52768210 |
| Pipeline adjusted | 12 | 0.65303915 | -0.65303915 |
| Pipeline realization adjusted | 4 | 0.25253672 | 0.00672615 |
| Pipeline realization adjusted | 8 | 0.37752342 | -0.24277524 |
| Pipeline realization adjusted | 12 | 0.53146164 | -0.44600512 |

Pipeline realization adjustment has the lowest full-scale WAPE at each horizon. It is nearly unbiased at four weeks but underforecasts at eight and twelve weeks. No-look-ahead tests passed for the origin-specific realization ratio.

## Reproducibility and scale

- Current full-scale repro: **PASS**, 46 canonical artifacts, same-seed hashes and CSV row counts identical, logical SQLite dump SHA-256 identical, and 39 artifacts changed for seed `20261023`.
- Full generation plus validation: **87.16 seconds**, sampled peak process-tree working set **739.9 MiB** on Windows/Python 3.14.7.
- Starter manifest file hashes matched under Python 3.11.15 and 3.14.7; the top-level runtime version in the manifest is expected to differ.
- GNU Make was not installed locally; direct commands passed. Remote CI was not run and is not claimed.
