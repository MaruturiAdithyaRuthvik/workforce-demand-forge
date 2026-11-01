# Adversarial self-audit

Audit run on 2026-11-01 against seed `20261022` on Windows. Commands and outputs below are from this session. `N/A` means the section found no code defect requiring a fix; commit hashes identify the commits that repaired discovered issues.

## A. Full scale

**Command:** `uv run wdf generate --scale full --seed 20261022 --out output/full` (run under a PowerShell process-tree working-set sampler at 250 ms intervals).

**Key output:**

```text
Generated 47 artifacts in output\full
Validation: PASS
WALL_SECONDS=87.158 PEAK_TREE_RSS_MIB=739.9
```

`config/scale_full.yaml` reports employees `5000`, skills `300`, projects `500`, roles `40`. The independent check verified all 53 weeks `2026W01`–`2026W53`, every ID regex, and the counts below. Example IDs: `EMP-000001`, `SKL-000083`, `PRJ-2026-000001`, `DEM-PRJ-2026-000001-2026W41`, and `ALLOC-2026-000001`.

| Table | Rows |
|---|---:|
| roles | 40 |
| skills | 300 |
| proficiency_scale | 5 |
| role_skills | 191 |
| employees | 5,000 |
| employee_skills | 57,595 |
| projects | 500 |
| demand_plans | 4,079 |
| demand_lines | 6,277 |
| leave | 12,001 |
| holidays | 6 |
| allocations | 7,535 |
| training | 251 |
| lifecycle_events | 19,620 |
| availability | 265,000 |
| utilization | 265,000 |
| supply | 4,389 |
| gap_analysis | 4,389 |
| gap_actions | 2,151 |

**Verdict:** PASS. Runtime is below the 180-second threshold; sampled peak process-tree working set was 739.9 MiB. A sub-250-ms peak could be missed.

**Fix commit:** `2dbdbfb` (indexed anomaly and trace processing; current full-scale runtime and same-seed behavior are recorded above and in section J).

## B. Data realism

**Command:** `uv run python -` (seeded calculations over the freshly generated `output/full/*.json`; seed `20261022`).

| Measure | Target used for this audit | Actual | Verdict |
|---|---:|---:|---|
| Part-time employee share | approximately 30% (25–35% audit band) | 31.380% (1,569/5,000) | PASS |
| Expired skill rate by expiry date | 12–18% | 15.055% (8,671/57,595) | PASS |
| Proficiency levels 2–3 | majority | 68.193%; counts 1: 2,910; 2: 17,343; 3: 21,933; 4: 11,388; 5: 4,021 | PASS |
| Skill popularity | heavy-tailed; max at least 3× median and top 10 exceed 10% | min 97; median 142.5; p90 295; max 1,988; top-10 share 29.188% | PASS |
| Project team size (distinct allocated employees) | visible spread | min 3; median 13; p90 26; max 64; zero projects 0 | PASS |
| Leave coverage and seasonality | 70–90% coverage; all months, summer/December peaks | 4,001/5,000 (80.020%); 12,001 leave rows; average 9.598 inclusive days per employee; monthly starts below | PASS |
| Employee-weeks with zero availability | a few percent | 8,001/265,000 (3.019%) | PASS |
| Injected anomaly rate per eligible population | 1–3% | see type table below | PASS |

| Issue type | Injected | Eligible denominator | Actual rate |
|---|---:|---:|---:|
| ALLOC_EXCEEDS_AVAILABILITY | 79 | 3,965 isolated Shared-Pool allocations | 1.992% |
| STALE_SKILL_TREATED_CURRENT | 173 | 8,671 expired EmployeeSkill rows | 1.995% |
| DEMAND_DOUBLE_COUNTED | 121 | 6,064 eligible Approved demand lines | 1.995% |
| OVERLAPPING_PROJECT_ASSIGNMENT | 31 | 1,537 eligible Dedicated-Team allocations | 2.017% |

Leave starts by month: Jan 827; Feb 829; Mar 838; Apr 818; May 800; Jun 941; Jul 1,610; Aug 1,400; Sep 758; Oct 771; Nov 815; Dec 1,594. Skill selection uses seeded power-law weights; project assignment uses seeded log-normal weights with at least one employee per project. The measured max/median skill popularity ratio is 13.95×.

**Verdict:** FIXED. The observed part-time, stale-skill, proficiency, heavy-tail, project-size, leave, and zero-availability measures meet the stated targets.

**Fix commits:** `788ddfe` (skill and project distributions), `3b52bef` (allocations), `f57246c` (leave).

## C. Independent integrity check

**Command:** `uv run python tools/independent_check.py output/full`.

The checker imports only Python standard-library `csv`, `sqlite3`, `datetime`, `re`, and `sys`; it does not import `wdf`, Pydantic, NumPy, pandas, or `json`. It checks CSV primary keys, every declared FK, enums, IDs, dates, weekly availability/capacity, utilization, 1,000 deterministic gap samples and traces, lifecycle state, duplicate Approved demand labels, then executes `schema.sql` and `seed.sql` in a fresh SQLite database with foreign keys on.

**Key output:**

```text
PASS PK uniqueness for 19 tables
PASS CSV foreign keys and lifecycle entity references
PASS enum, exact ID regex, ISO-week, and date-format checks
PASS date ordering and demand-week date agreement
PASS availability arithmetic and capacity reconciliation: 53 weeks
PASS utilization recompute for 265000 employee-weeks
PASS demand/supply/gap recompute and traces for 1000 stratified gaps
PASS lifecycle latest state matches current state
PASS approved-demand duplicate groups match injected labels: 121
PASS fresh SQLite seed load and PRAGMA foreign_key_check
RESULT: PASS (10 independent checks)
```

**Verdict:** PASS.

**Fix commits:** `42443cf` (checker and Make target), `2516b85` (stratified gap sample).

## D. Traceability spot check

**Command:** `uv run python -` with `random.Random(20261101).sample(gap_rows, 25)`. Each demand ID was resolved and checked for matching week/role/skill. Each supporting ESK was checked for matching skill, Current flag, expiry on/after `2026-10-22`, and proficiency meeting the minimum of the linked demand lines.

**Key output:** `25 of 4389 GapAnalysis rows`; `demand_line_links=30/30`; `supporting_esk_links=69/69`; `linked actions resolved=9`.

| Gap ID | Source demand line IDs | Supporting ESK IDs | Linked actions: ID / rule / owner / assumptions |
|---|---|---|---|
| GAP-2026W15-000746 | DEML-005406 | ESK-009729, ESK-024940, ESK-032434, ESK-046904 | none |
| GAP-2026W18-000949 | DEML-000940 | ESK-039229, ESK-055605 | none |
| GAP-2026W41-003229 | DEML-001597 | none | GACT-000916 / GAP_TRAIN_MEDIUM / Manager / gap_fte=0.7676; adjacent skill SKL-000054; thresholds low=0.5, medium=2.0 |
| GAP-2026W12-000490 | DEML-000965, DEML-003973 | ESK-021093, ESK-035181 | none |
| GAP-2026W10-000356 | DEML-001488 | ESK-013667, ESK-027686, ESK-031493 | GACT-000080 / GAP_TRAIN_MEDIUM / Manager / gap_fte=0.5512; adjacent skill SKL-000006; thresholds low=0.5, medium=2.0 |
| GAP-2026W11-000414 | DEML-004110 | ESK-007747, ESK-008065, ESK-047533 | none |
| GAP-2026W27-001796 | DEML-002716, DEML-003640, DEML-003698 | none | GACT-000481 / GAP_TRAIN_MEDIUM / Manager / gap_fte=1.8015; adjacent skill SKL-000162; thresholds low=0.5, medium=2.0 |
| GAP-2026W32-002251 | DEML-005749 | ESK-003552, ESK-011597, ESK-022286, ESK-028151, ESK-029674, ESK-047727, ESK-052155 | none |
| GAP-2026W36-002699 | DEML-002001 | ESK-033837 | GACT-000745 / GAP_REVERIFY_SMALL / Employee / qualified stale skill; gap_fte=0.3284 < low_gap_fte=0.5 |
| GAP-2026W19-001027 | DEML-003438 | ESK-005828, ESK-016555, ESK-025043, ESK-031360, ESK-041250, ESK-050324 | none |
| GAP-2026W20-001164 | DEML-003559 | ESK-057476 | none |
| GAP-2026W45-003658 | DEML-004050 | ESK-017978, ESK-024474, ESK-031985, ESK-056724 | none |
| GAP-2026W48-004003 | DEML-003324 | ESK-002766 | GACT-001141 / GAP_REVERIFY_SMALL / Employee / qualified stale skill; gap_fte=0.1899 < low_gap_fte=0.5 |
| GAP-2026W20-001117 | DEML-001192, DEML-002708, DEML-005238 | ESK-034732, ESK-041881, ESK-052625 | GACT-000286 / GAP_REVERIFY_SMALL / Employee / qualified stale skill; gap_fte=0.0316 < low_gap_fte=0.5 |
| GAP-2026W02-000012 | DEML-000115 | ESK-057476 | GACT-000004 / GAP_TRAIN_MEDIUM / Manager / gap_fte=1.9327; adjacent skill SKL-000016; thresholds low=0.5, medium=2.0 |
| GAP-2026W38-002897 | DEML-003919 | ESK-042207 | none |
| GAP-2026W08-000216 | DEML-004108 | ESK-025551, ESK-043910 | none |
| GAP-2026W49-004029 | DEML-002564 | none | GACT-001152 / GAP_TRAIN_MEDIUM / Manager / gap_fte=0.7312; adjacent skill SKL-000104; thresholds low=0.5, medium=2.0 |
| GAP-2026W40-003179 | DEML-006070 | ESK-051781 | none |
| GAP-2026W16-000847 | DEML-000968 | ESK-039155 | none |
| GAP-2026W49-004064 | DEML-000507 | ESK-017978, ESK-024474, ESK-031985, ESK-056724 | none |
| GAP-2026W04-000056 | DEML-000655 | ESK-011389, ESK-018328, ESK-034174 | none |
| GAP-2026W24-001528 | DEML-005199 | ESK-004459, ESK-005642, ESK-006861, ESK-025977, ESK-032890, ESK-036774 | none |
| GAP-2026W17-000893 | DEML-001269 | none | GACT-000226 / GAP_REVERIFY_SMALL / Employee / qualified stale skill; gap_fte=0.4047 < low_gap_fte=0.5 |
| GAP-2026W36-002704 | DEML-000432 | ESK-001031, ESK-010925, ESK-012572, ESK-017738, ESK-019657, ESK-019809, ESK-022564, ESK-039623, ESK-046117, ESK-046723, ESK-048116, ESK-051204, ESK-057128 | none |

Five utilization examples show the effect of leave on the two utilization bases:

| Utilization ID | Employee | Week | Capacity h | Available h | Leave h | Utilization available | Utilization capacity |
|---|---|---|---:|---:|---:|---:|---:|
| UTL-000016-2026W21 | EMP-000016 | 2026W21 | 40.0 | 16.0 | 24.0 | 0.5000 | 0.2000 |
| UTL-000019-2026W45 | EMP-000019 | 2026W45 | 40.0 | 32.0 | 8.0 | 0.5000 | 0.4000 |
| UTL-000024-2026W28 | EMP-000024 | 2026W28 | 20.0 | 16.0 | 4.0 | 0.7500 | 0.6000 |
| UTL-000032-2026W09 | EMP-000032 | 2026W09 | 40.0 | 32.0 | 8.0 | 0.5000 | 0.4000 |
| UTL-000040-2026W43 | EMP-000040 | 2026W43 | 32.0 | 19.2 | 12.8 | 1.0000 | 0.6000 |

Exception paths: 348/450 `UTIL_CONTRACT_OVER_THRESHOLD` Contract actions were Escalated at the budget cap (example `GACT-001253`, source `UTL-000111-2026W22`, estimated cost 960.00 > cap 750.00); 10 `TRAIN_FAILED_FALLBACK` Hire actions were emitted (example `GACT-000001`, failed training `TRN-000251` for `EMP-000001`/`SKL-000281`); one Cancelled project retained one open Active allocation (`PRJ-2026-000002` / `ALLOC-2026-000281`).

**Verdict:** PASS; every sampled trace resolved, five ratio differences reconciled to leave, and each required exception path is present.

**Fix commits:** `7fa90c3` (utilization actions), `788ddfe` (cancellation fixture).

## E. Anomaly and detector honesty

**Commands:** `uv run wdf detect --input output/full`; `uv run wdf evaluate --input output/full`; `uv run python -` for seed `20261024` and cross-type checks on seeds `20261022`–`20261024`; `rg -n 'ground_truth|groundtruth' wdf/detect.py`; `uv run pytest -q tests/test_p6.py::test_detection_runs_without_ground_truth`.

The deletion test generated an output directory, removed its `ground_truth` folder, called `run_detection`, and passed. The grep found no ground-truth import/path in `wdf/detect.py`; `run_detection` loads source tables only. The source-table field scan covered 113,400 full-scale source rows and found no suspicious ground-truth, issue-type, injected-ID, or expected-decision fields.

| Seed | Issue type | Injected | Detected | TP | FP | FN | Precision | Recall | F1 |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 20261022 | ALLOC_EXCEEDS_AVAILABILITY | 79 | 79 | 79 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| 20261022 | DEMAND_DOUBLE_COUNTED | 121 | 121 | 121 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| 20261022 | OVERLAPPING_PROJECT_ASSIGNMENT | 31 | 31 | 31 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| 20261022 | STALE_SKILL_TREATED_CURRENT | 173 | 173 | 173 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| 20261023 | ALLOC_EXCEEDS_AVAILABILITY | 80 | 80 | 80 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| 20261023 | DEMAND_DOUBLE_COUNTED | 122 | 122 | 122 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| 20261023 | OVERLAPPING_PROJECT_ASSIGNMENT | 30 | 30 | 30 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| 20261023 | STALE_SKILL_TREATED_CURRENT | 168 | 168 | 168 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| 20261024 | ALLOC_EXCEEDS_AVAILABILITY | 82 | 82 | 82 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| 20261024 | DEMAND_DOUBLE_COUNTED | 126 | 126 | 126 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| 20261024 | OVERLAPPING_PROJECT_ASSIGNMENT | 28 | 28 | 28 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| 20261024 | STALE_SKILL_TREATED_CURRENT | 181 | 181 | 181 | 0 | 0 | 1.000 | 1.000 | 1.000 |

No false-positive or false-negative examples exist in these runs, so there are no IDs to explain. A 1.000 score is plausible because the injector creates records that satisfy the same deterministic predicates used by the detector; it is not evidence of production accuracy. Across all three seeds, no ground-truth record ID has multiple labels, no type-(d) injected record is detected as type-(a), and no unlabeled cross-type detections occurred.

| Issue family | Near-miss hard-negative records (flagged) |
|---|---:|
| ALLOC_EXCEEDS_AVAILABILITY: exact-100% Shared-Pool overlap groups | 1,950 (0) |
| STALE_SKILL_TREATED_CURRENT: expiry exactly on as-of date | 1 (0) |
| DEMAND_DOUBLE_COUNTED: same role/skill in adjacent weeks | 67 (0) |
| OVERLAPPING_PROJECT_ASSIGNMENT: adjacent, non-overlapping Dedicated-Team allocations | 6 (0) |

Additional boundary fixtures include one part-time 100%-allocation W52 case and one five-day leave record. `tests/test_p5.py::test_programmatic_near_miss_fixtures_are_not_detected` verified that each fixture family is nonempty and none of its records is flagged.

**Verdict:** FIXED; detection no longer requires ground truth. Scores are exact on these generated seeds, with the synthetic-rule caveat above.

**Fix commit:** `f627ed5`.

## F. Forecast

**Commands:** `uv run wdf forecast --input output/full`; `uv run pytest tests/test_p4.py -q`.

The rolling-origin backtest evaluates 36, 32, and 28 origins at the 4-, 8-, and 12-week horizons respectively.

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

No-look-ahead tests passed (`2 passed`), including the origin-specific realization ratio. The calibrated pipeline method wins full-scale WAPE at all three horizons; it is nearly unbiased at four weeks but underforecasts at eight and twelve weeks. Moving average also underforecasts. The uncalibrated pipeline method has bias equal to negative WAPE because every evaluated prediction is below actual; this is explained in `docs/DESIGN_DECISIONS.md`.

**Verdict:** PASS; limits and horizon-dependent results are documented.

**Fix commit:** `2167eaf`.

## G. Reproducibility (earlier audit run; final rerun in J)

The following paired values record the prior full-scale audit run. The item 9 final run below supersedes these values for the current generator.

**Command:** `uv run wdf repro --scale full --seed 20261022 --out output`.

**Key output:** `Reproducibility: PASS (46 files)`; `same_seed_hashes_match=true`; `same_seed_row_counts_match=true`; `same_seed_logical_database_match=true`; `different_seed_hashes_differ=true`; 39 of 46 canonical files changed with seed `20261023`. Versions recorded in the manifest/report: Python `3.14.7`, NumPy `2.3.3`, pandas `3.0.0`. Logical database SHA-256 was `426cec3ff346024c501b8f43b96140530de128a4f54a8b85db475312d3f784fb` on both runs.

Every reported CSV row count matched between the two runs:

| CSV file | Rows A | Rows B |
|---|---:|---:|
| allocations.csv | 5,025 | 5,025 |
| availability.csv | 265,000 | 265,000 |
| demand_lines.csv | 6,193 | 6,193 |
| demand_plans.csv | 4,024 | 4,024 |
| employee_skills.csv | 57,595 | 57,595 |
| employees.csv | 5,000 | 5,000 |
| forecast.csv | 800 | 800 |
| gap_actions.csv | 1,939 | 1,939 |
| gap_analysis.csv | 4,316 | 4,316 |
| ground_truth/ground_truth.csv | 394 | 394 |
| holidays.csv | 6 | 6 |
| leave.csv | 651 | 651 |
| lifecycle_events.csv | 17,002 | 17,002 |
| proficiency_scale.csv | 5 | 5 |
| projects.csv | 500 | 500 |
| role_skills.csv | 191 | 191 |
| roles.csv | 40 | 40 |
| skills.csv | 300 | 300 |
| supply.csv | 4,316 | 4,316 |
| training.csv | 251 | 251 |
| utilization.csv | 265,000 | 265,000 |

The report stores the A and B SHA-256 for each path. Since every pair matches, each value below is the SHA-256 for both runs:

| Canonical file | SHA-256 (A = B) |
|---|---|
| allocations.csv | `389237a10208bff796c07d326ca76e2eaac08bb5a7a349d1e7ba9f8cacb269fe` |
| allocations.json | `8b4950bb3f1e69369011558164c2a8f5862bf4ba2f3a5f0718a66ea889bef1b9` |
| availability.csv | `1aa15a62bd38990b6f3482d8fd0ce9acea0d2273c93f90bf22dffa83a7021f73` |
| availability.json | `a62ac2eae51c2368718aadcf1f3af8fa3c7ae98f7914e86992b66a7aa939328d` |
| demand_lines.csv | `2378208e298a85444cef9323cb2f44c8c795cdcf05e70761aa2b4dc05f11a993` |
| demand_lines.json | `6525a944a954f1f048296c47d346a0f85b73a348114259e21f98499574dd984a` |
| demand_plans.csv | `5721bcbb52cf91dfb013ee18a8d3f01b17a1daf7988de7255674b0b5bfc6d61b` |
| demand_plans.json | `9ef01773d7eb7c76477718ce08e3e3d9c5a90a363649586ec4ae8c6be078008c` |
| employee_skills.csv | `cfd6d0b3e2d09a075a081b2a2bbf67776fd395f1d42858f2c57f297a2e4f23cd` |
| employee_skills.json | `4cb6141c779e80504f9cda93daa186d3cb1e2503277a0b5be30c7e1b2e731607` |
| employees.csv | `a10a02314fbacf6a27f6a75d596c39d5a16c07654bea007dbfeff40c3b2422cb` |
| employees.json | `cc1461710ef38563ffefd86a52b66863d98b23faa89bbe77d8f955b9e65a90da` |
| forecast.csv | `6010cf16337e0462bc46bb77a3c41e941150eff044a9655785a373cfb8dc19e9` |
| gap_actions.csv | `b216c81d798891331994e7fc0d08f2be22c1d1c860130e710e170de831bd58ae` |
| gap_actions.json | `b5c9181ba002833a56d98223261b7774b060370a9b421b1866f1eca54a289f8d` |
| gap_analysis.csv | `aaee0d972dd5049f2d8f576157d0ba87b866256f4d78fabc246f9c6c121c4327` |
| gap_analysis.json | `ed588235172984693c625bc1b4abe40f9802e608460cc0ad2993c387a3d4e873` |
| ground_truth/ground_truth.csv | `356164b14e354f6edb23cef6ec554d80e69738f1c984460cf164d9fde9cb074c` |
| ground_truth/ground_truth.json | `81cea05e1af9d8bb4146d3850e569dd88fc9ef951d5a4530a615007038dc5354` |
| holidays.csv | `5711c21093aebd2ba01b16b87b3aca0d47fb612f2c03dbe2d8d59dd75918fffe` |
| holidays.json | `28199297d67197d153827ef093f72abe36ced5ab463748e5b18410d584d720c7` |
| leave.csv | `0ad419c61790cffdb9a9ae9cafa997c7a9321376daf05276c19e6edf3c7b16e1` |
| leave.json | `585429c0a0e04afa282c837cbff6299b3f16d34e665716f7d09ad6b32192a835` |
| lifecycle_events.csv | `68e8bde00e5d497654362a2bf0516c642d4c9ed3460355909581c0750d51996d` |
| lifecycle_events.json | `93e22a3fabed751e8cb8c4439af3336ef8facd9414a40df1065c62034955201f` |
| manifest.json | `0616ac4e87c4fc2a4273194a572200d8bedadca898a45443c98c8c4e468f4f98` |
| metrics.json | `687cb4a6483a75bcfe3662c47da7eb835f10b0213b4e1ac045527f2fdd0a196a` |
| proficiency_scale.csv | `27f5db839505a2ac7d13362e70b6a530157958baa84a987c939f180b38d74221` |
| proficiency_scale.json | `4db213c4d0a2ac1959d64f520c8eeb0f5ae1b4f7a2dc5c6dfd792848b58e242c` |
| projects.csv | `26ea2d05e90ffe7698876aff1674685f95d34de54df25d36c59e1aa715689d7b` |
| projects.json | `27bd5167b53286b4330ce609da41c986db3b67a03761e6f313616d36dfac50a1` |
| role_skills.csv | `0f637b732016376c3a22d0da7ed524b89ca990c4a0a384778445cd95da3208e5` |
| role_skills.json | `c4f08257281474da69d261e01afc6925b0d86dd8a75107228818fc7b1635fca3` |
| roles.csv | `8b13b2267412a6e3d622d48548175b11030f297269dcf98f67d576f4fda1c71b` |
| roles.json | `d495f704a6caa55db151278bc8c7db884e694fda1da3b4ed84db7b4eebfec918` |
| schema.sql | `f5c736339d71fc31e828a65600e86a7a3454e3468685815aa82082e2b7798dab` |
| seed.sql | `2dbd2cb400833aaae1a5bc7263b7afd7cc09b43e9b47ea8a4fe18a1cd517f24c` |
| skills.csv | `4183c1b7d8ca1be88087d9f0609b309df7ff7ed7621fa464e5746e0e49a2b0ea` |
| skills.json | `46baae039234910926f14bbec8a1d3f9f94f538727a3793ad6a4328eacb28a0f` |
| supply.csv | `0e5c5abd1b0304e9ab0bc6858a7e51f66b5a73a6200d88f927f2b289b25d0a50` |
| supply.json | `db61f734c3d032c6017764b4fcb9bbd18f257b3186c5e65778aee38c99f37ac2` |
| training.csv | `ad9b9f707edcf39a3019d13faf7fb332a4c4b5d52497a1f9492a973b0c5a593a` |
| training.json | `0abf7598d20445aa343008a2897708b2c5f9521ed17d748ea9387b00863d1d37` |
| utilization.csv | `eeff13a03bb1ce5ec367b5f8328bd1afbf903a69a84f48c4bc49c71e9d40e269` |
| utilization.json | `f63c18222b266ad11102d53a0952b60c49e0f9e2e15d89bcd51e939131a1feaa` |
| validation_report.json | `38cd62fe368e65d43536ce1d55ee924bde97047909e88b96691332f5abcd82a6` |

The 39 changed paths for the different seed were allocations, availability, demand lines/plans, employee skills, employees, forecast, gap actions/analysis, ground truth, leave, lifecycle events, manifest, metrics, projects, role skills, seed SQL, skills, supply, training, utilization, and validation report (the applicable CSV/JSON variants).

**Command:** scan each of the 46 files named in `sha256` for ISO wall-clock timestamps and absolute Windows/UNC/Unix paths.

**Key output:** `Hashed artifacts with wall-clock timestamps: []`; `Hashed artifacts with absolute paths: []`.

**Verdict:** PASS; `run_repro` now records both hashes and both CSV row counts per path.

**Fix commit:** `35b5f94`.

## H. Repository hygiene (earlier audit measurement; final rerun in J)

The file counts, lock counts, and coverage below are retained as historical evidence. Section J records final hygiene checks against the current tree.

**Commands:** `rg -n '\b52\b' wdf`; `rg -n '\b(TODO|FIXME)\b' wdf tests tools`; `rg -n '\bprint\(' wdf`; secret/contact `git grep` patterns; `$files = git ls-files; $sum = ($files | ForEach-Object { (Get-Item -LiteralPath $_).Length } | Measure-Object -Sum).Sum`; lock audit using `tomllib`; `uv lock --check`; fresh local `git clone`, followed by each README quickstart command.

**Key output:**

```text
wdf\anomalies.py:199: boundary_week = date.fromisocalendar(2026, 52, 1)
TODO/FIXME matches: none
Debug print matches in wdf: none
No credentials patterns found
No email patterns found
No phone patterns found
Tracked env/key files: none
Tracked files=97 bytes=23226822 MB=22.15
Files over 5 MB: output/starter/seed.sql 8.39 MB
uv.lock package records 25 exact nonempty versions 25; packages without versions []
requirements-lock exact pins 24; loose/unpinned entries []
```

The sole literal `52` is an explicit W52 boundary fixture, not a 52-week calendar assumption. The numeric-literal scan found fixed synthetic/business parameters and identifiers (e.g. 40 capacity hours, 0.22 demand omission, 0.12 leave chance, 1.25 anomaly allocation, forecast horizons 4/8/12); no year-length calculation relies on 52. `requirements-lock.txt` now includes the exact build backend `setuptools==80.9.0`.

`make` is unavailable in this environment, so `make independent-check` could not be invoked; the equivalent `uv run python tools/independent_check.py output/full` passes. The target is present in `Makefile`.

Fresh-clone commands: `git clone --quiet --no-hardlinks . $clone`; `uv sync --locked --extra dev`; then the five `uv run wdf` generate/validate/forecast/detect/evaluate commands listed in README Quickstart.

Fresh-clone output: `uv sync --locked --extra dev` installed 25 locked packages under Python 3.11.15; generation and validation passed; forecast completed for 10 weeks; detection found 19 starter anomalies; evaluation completed for seeds 20261022/20261023; `FRESH_CLONE_QUICKSTART=PASS`.

The initial `pytest --cov` attempt failed because `pytest-cov`/coverage was not installed. The full suite was rerun using the temporary runner `uv run --with coverage==7.10.6 coverage run ...`; result was 25 passed, total coverage 89%. CLI module coverage is 0% in the unit-test run; CLI workflows were exercised in the fresh clone. `uv run ruff check wdf tests tools` passed; `uv lock --check` reported `Resolved 25 packages`.

**Verdict:** FIXED. README commands now use `uv run`, the build backend is in the dev lock, secret/contact scans found no patterns, and the clean-clone quickstart passed. Make remains unavailable.

**Fix commit:** `d9d8dff`.

## I. Documentation completeness

**Commands:** `uv run python tools/check_docs.py output/starter`; `uv run python tools/check_docs.py output/full`; `Test-Path docs\PROBLEM.md`; `uv run wdf generate --scale starter --seed 20261022 --out output/starter`.

**Key output:**

```text
PASS data dictionary: 19 tables, 126 Pydantic fields
PASS SOURCE_MANIFEST.md states synthetic records and no external data
PASS manifest checksums and inventory: 49 files
docs\PROBLEM.md: True
```

`docs/TRACEABILITY.md` maps every numbered line 1–55 of the supplied statement, including steps 1–10, edge cases, acceptance criteria, evaluation focus (a)–(g), provenance, and submission requirements. It explicitly lists incomplete project-level forecasting and the unverified public push. README figures are refreshed from the current starter/full outputs. `docs/PROBLEM.md` is committed unchanged as requested.

**Verdict:** PASS for schema, manifest, and line-referenced documentation checks; remaining functional/documentation gaps are explicit below.

**Fix commits:** `42443cf` (checker); final audit commit (source statement and traceability map).

## Remaining known gaps

| Gap | Evidence/status |
|---|---|
| Forecast output is role/week, not project/role/week | `wdf/forecast.py` does not retain `project_id`; project-level demand forecasting is incomplete |
| Stale-skill injection uses an expired skill incorrectly marked `Current` | It does not model a separate stale proficiency value; the currency/expiry detector case is still covered |
| One Active allocation remains on a Cancelled project | Deliberate exception fixture, not a production cancellation policy |
| Public GitHub push is unverified | This local audit neither pushed nor verified a public repository |
| GNU Make and remote GitHub Actions were not run locally | `make` is unavailable on this Windows machine; direct `uv run` equivalents passed, but CI is not claimed |
| Zero-availability target was unspecified | Current full result is 3.019% of employee-weeks |
| Perfect detector metrics are synthetic-rule results | All three seeds have zero FP/FN because deterministic injection matches detector predicates; this does not establish real-world accuracy |
| CLI test coverage is 55%; one `CliRunner` smoke test covers `generate` | Other README commands were exercised in the fresh-clone quickstart |

## J. Follow-up review (before/after and final rerun)

**Command:** `uv run python -` (stdlib calculations over `output/full/*.json`; forecast below-actual share recomputed over the existing rolling-origin forecasts using `wdf.forecast._predictions`).

**Key output:**

```text
allocations_per_employee distribution (allocations: employees): {1: 4975, 2: 25}
employees with 2+ allocations: 25/5000 = 0.500%
employees with overlapping allocation date ranges: 24/5000 = 0.480%
employees with >=1 leave record: 651/5000 = 13.020%
leave starts/month: {'02': 145, '05': 161, '07': 178, '12': 167}
inclusive leave days total=2726; average per employee=0.545
zero-availability employee-weeks: 131/265000 = 0.049%
GapAction counts by action_type: {'Hire': 339, 'Reallocate': 412, 'Reverify': 138, 'Train': 1050}
GapAction counts by rule_id: {'GAP_HIRE_LARGE': 321, 'GAP_REVERIFY_SMALL': 138, 'GAP_TRAIN_MEDIUM': 1050, 'TRAIN_FAILED_FALLBACK': 18, 'UTIL_OVER_AVAILABLE': 412}
over-utilized employee-weeks (allocated_hours > available_hours): 412; UTIL_OVER_AVAILABLE actions: 412
forecasts below actual (moving_average_4w): 16857/29440 = 57.259%
forecasts below actual (pipeline_adjusted): 27776/29440 = 94.348%
```

The allocation and leave metrics are below the follow-up targets. The baseline has 412 over-utilized employee-weeks and 412 utilization actions, but actions carry no week field, so exact employee-week action linkage is not auditable yet. Leave starts occur in only four months. Forecast undershoot is especially frequent for the pipeline method.

The originally written `2/5000` was a counting error: the distribution is by employee count, so its `2` bucket means 25 employees with two allocations each. The corrected share is 25/5,000 (0.500%).

**Verdict:** Baseline captured before changes; deficiencies are the targets of items 1–8. The corrected allocation share is derived directly from the displayed distribution.

**Fix commit:** N/A (measurement only).

### Item 7 portability evidence

**Commands:** isolated `uv run --python 3.11.15 --locked wdf generate --scale starter --seed 20261022`; repeat with `--python 3.14.7`; compare `manifest.json` file-to-SHA256 mappings; `uv sync --locked`; `uv lock --check`; `git check-attr text eol -- output/starter/allocations.csv output/starter/seed.sql output/starter/manifest.json`.

**Key output:**

```text
Python versions: 3.11.15 3.14.7
same artifact inventory: True count: 47
identical manifest artifact hashes: True
different artifact hashes: []
same dependency versions: True
manifest runtime field differs: True
Checked 25 packages
Resolved 25 packages
csv/sql/json: text set; eol=lf
```

The one cross-version artifact mismatch before correction was `metrics.json`, caused only by floating-point accumulation deltas up to `8.3e-15`; rounding WAPE/bias to 8 decimals made all 47 manifest-declared artifact hashes identical. The manifest's top-level `python_version` remains intentionally runtime-specific; its file hash inventory is stable across the two tested versions. `Get-Command make` found no local Make executable, so the GitHub Actions workflow could not be executed locally; CI success is not claimed.

### Item 8 config and coverage evidence

**Commands:** `uv add --dev pytest-cov==7.0.0`; `uv export --locked --format requirements-txt --all-groups --no-emit-project -o requirements-lock.txt`; `uv run ruff check .`; `uv run pytest --cov=wdf --cov-report=term-missing`; `uv lock --check`; `uv run python tools/check_docs.py output/starter`; `uv run python -c "from wdf.config import load_settings; ..."`; and a detached worktree at pre-item-8 commit `94e2b80` generating starter seed `20261022`, compared file hashes with the post-change generator.

**Key output:**

```text
pytest-cov==7.0.0; coverage==7.17.0; exact pins exported to requirements-lock.txt
31 passed; total coverage 92%; CLI coverage 55%
Ruff: All checks passed!
uv lock --check: Resolved 27 packages
default values: weekly_hours=40.0, zero_demand_probability=0.22, leave_employee_share=0.8, allocation_anomaly_percentage=1.25
pre-item-8 / post-item-8: 47 artifacts each; identical=True; mismatches=0
docs check: 19 tables, 126 Pydantic fields; manifest inventory 49 files
```

The detached worktree comparison verifies the moved defaults preserved the generator's artifact output. The checked-in `output/starter` is older than the current source generator: its manifest contains two extra detection files, and it differs from the just-generated current output. This stale sample will be regenerated and checked against fresh output during item 9. `make` is unavailable locally, so the Make target itself was not invoked; the equivalent coverage-enabled pytest command passed. The GitHub Actions workflow has not been run remotely.

**Verdict:** PASS for item 8. Full-scale and final sample refreshes remain item 9.

**Fix commit:** `7c47949`.

### Item 9: before/after measures and final rerun

**Commands:** `uv run python -` for allocation, leave, action, and forecast comparisons; `uv run wdf forecast --input output/full`; `uv run wdf detect --input output/full`; `uv run wdf evaluate --input output/full`.

| Measure | Before item 1 changes | Final full export |
|---|---:|---:|
| Allocations | 5,025 | 7,535 (1.507x employees) |
| Employees with 2+ allocations | 25/5,000 (0.500%) | 2,515/5,000 (50.300%) |
| Employees with overlapping allocation date ranges | 24/5,000 (0.480%) | 1,032/5,000 (20.640%) |
| Employees with at least one leave record | 651/5,000 (13.020%) | 4,001/5,000 (80.020%) |
| Total inclusive leave days; average per employee | 2,726; 0.545 | 47,989; 9.598 |
| Employee-weeks with zero availability | 131/265,000 (0.049%) | 8,001/265,000 (3.019%) |
| Over-utilized employee-weeks | 412 | 450 |
| Over-utilized weeks linked to a source-utilization action | Not auditable from the old actions | 450/450; 900 linked Reallocate/Contract actions |

The final leave starts cover every month: Jan 827; Feb 829; Mar 838; Apr 818; May 800; Jun 941; Jul 1,610; Aug 1,400; Sep 758; Oct 771; Nov 815; Dec 1,594.

The pre-injection final allocation baseline had 7,502 rows (1.5004x employees), 1,500 employees with sequential allocations, 1,000/5,000 employees with legal Shared-Pool overlaps, and zero Dedicated-Team overlap pairs. In the exported data after anomaly injection, 976/5,000 (19.520%) employees retain legal Shared-Pool overlaps when type-(d) injected cases are excluded; the total date-overlap share includes injected cases.

| GapAction measure | Before item 1 changes | Final full export |
|---|---|---|
| Counts by action type | Hire 339; Reallocate 412; Reverify 138; Train 1,050 | Contract 450; Hire 199; Reallocate 450; Reverify 146; Train 906 |
| Utilization rules | `UTIL_OVER_AVAILABLE` 412 | `UTIL_OVER_AVAILABLE` 450; `UTIL_CONTRACT_OVER_THRESHOLD` 450 |
| Over-utilized weeks with traceable utilization source IDs | Not auditable | 450/450; 450 Reallocate and 450 Contract actions |

Forecasts below actual, recomputed from rolling-origin predictions using data available before each origin:

| Method | Horizon | Below actual | Share |
|---|---:|---:|---:|
| Moving average | 4 weeks | 3,014/5,760 | 52.326% |
| Moving average | 8 weeks | 5,739/10,240 | 56.045% |
| Moving average | 12 weeks | 8,002/13,440 | 59.539% |
| Pipeline adjusted | 4 weeks | 5,404/5,760 | 93.819% |
| Pipeline adjusted | 8 weeks | 9,685/10,240 | 94.580% |
| Pipeline adjusted | 12 weeks | 12,767/13,440 | 94.993% |
| Pipeline realization adjusted | 4 weeks | 2,328/5,760 | 40.417% |
| Pipeline realization adjusted | 8 weeks | 6,518/10,240 | 63.652% |
| Pipeline realization adjusted | 12 weeks | 10,039/13,440 | 74.695% |

The original baseline command reported the moving-average and pipeline shares aggregated across horizons as 16,857/29,440 (57.259%) and 27,776/29,440 (94.348%); the table above reports each final method/horizon separately. The realization-adjusted method reduces undershooting, but does not eliminate it at longer horizons.

**Final rerun commands:** `uv run wdf validate --input output/full`; `uv run python tools/independent_check.py output/full`; `uv run wdf forecast --input output/full`; `uv run wdf detect --input output/full`; `uv run wdf evaluate --input output/full`; `uv run python tools/check_docs.py output/starter`; `uv run python tools/check_docs.py output/full`; `uv run ruff check wdf tests tools`; `uv run pytest --cov=wdf --cov-report=term-missing`; `uv lock --check`.

**Key output:**

```text
Validation: PASS; errors=0; warnings=2
Independent audit: PASS (10 checks); 53 weeks; 265000 utilization rows; 1000 gap recomputations
Forecast complete for 10 future ISO weeks
Detected 404 anomalies
Evaluation completed for seed 20261022 and held-out seed 20261023
Docs: PASS; 19 tables, 126 Pydantic fields; manifest inventory 49 files (starter and full)
Ruff: All checks passed!
32 passed; total coverage 92%; CLI coverage 55%
uv lock --check: Resolved 27 packages
```

The three-seed full-scale detector results, near-miss counts, exception paths, and no-look-ahead test results are recorded in sections D–F. The final rerun of main-seed detection/evaluation completed; the held-out 20261024 metrics are from the separate full-scale held-out run recorded in section E.

### Full-scale reproducibility hashes and row counts

**Command:** `uv run wdf repro --scale full --seed 20261022 --out output/full-repro`.

**Key output:** `Reproducibility: PASS (46 files)`; same-seed hashes and CSV row counts matched; logical database hashes matched; 39/46 artifacts changed for seed `20261023`. Python `3.14.7`, NumPy `2.3.3`, pandas `3.0.0`; logical database SHA-256 for both runs: `0df3016bc569d6c824eab4e8d44f7c6c1959715320e5771aca0e41948116e6c5`. For example, `allocations.csv` changed from `9578eafa0cacd50cf79766e7a3c1d6f7cbac0d5ad827d95ee63a2d091b2a0322` to `2f4abd595340d265770623a3ccbf8d2c52a50b446059cf8ba280f13ac13edb83` for the different seed.

| File | SHA-256 run A | SHA-256 run B | CSV rows A/B |
|---|---|---|---:|
| allocations.csv | 9578eafa0cacd50cf79766e7a3c1d6f7cbac0d5ad827d95ee63a2d091b2a0322 | 9578eafa0cacd50cf79766e7a3c1d6f7cbac0d5ad827d95ee63a2d091b2a0322 | 7535/7535 |
| allocations.json | ba5e4879db3172e7d46bf59d7f4ee1ff013c73f20f1b70337c8279e2ed856e2f | ba5e4879db3172e7d46bf59d7f4ee1ff013c73f20f1b70337c8279e2ed856e2f | - |
| availability.csv | a259de214272ba4a6147c3f86d7d0f404cc77c68c728e978c372fab031d5ae4c | a259de214272ba4a6147c3f86d7d0f404cc77c68c728e978c372fab031d5ae4c | 265000/265000 |
| availability.json | cd4eba4771628b923627dd245751916e0f42ddd5bf377fb75b253fded7341250 | cd4eba4771628b923627dd245751916e0f42ddd5bf377fb75b253fded7341250 | - |
| demand_lines.csv | a2d6f66d7af68e878ba8acc757a4629074277aa97eebc8964446c640bbe7acce | a2d6f66d7af68e878ba8acc757a4629074277aa97eebc8964446c640bbe7acce | 6277/6277 |
| demand_lines.json | 466e57130df9aad87b246865d2fa0e1d3c7746aef271a4f030412e613854d238 | 466e57130df9aad87b246865d2fa0e1d3c7746aef271a4f030412e613854d238 | - |
| demand_plans.csv | d45eebe7ff732b6583e5677f57c5f5dd6bc1319fcde711139d59e7a3f6fb8ca3 | d45eebe7ff732b6583e5677f57c5f5dd6bc1319fcde711139d59e7a3f6fb8ca3 | 4079/4079 |
| demand_plans.json | 0486ecca19e9ad18bba61905d8fdd9f090d1c5c337bfd9c7060f3e4adbd6f4c4 | 0486ecca19e9ad18bba61905d8fdd9f090d1c5c337bfd9c7060f3e4adbd6f4c4 | - |
| employee_skills.csv | b85455d3da16ca04ec3f925447b37364588986233027dc0879d66c81d83934f1 | b85455d3da16ca04ec3f925447b37364588986233027dc0879d66c81d83934f1 | 57595/57595 |
| employee_skills.json | ab99dde1734f1600380bdc400ad147927b989cb44e3ab5b949d053c31d08dbb9 | ab99dde1734f1600380bdc400ad147927b989cb44e3ab5b949d053c31d08dbb9 | - |
| employees.csv | a10a02314fbacf6a27f6a75d596c39d5a16c07654bea007dbfeff40c3b2422cb | a10a02314fbacf6a27f6a75d596c39d5a16c07654bea007dbfeff40c3b2422cb | 5000/5000 |
| employees.json | cc1461710ef38563ffefd86a52b66863d98b23faa89bbe77d8f955b9e65a90da | cc1461710ef38563ffefd86a52b66863d98b23faa89bbe77d8f955b9e65a90da | - |
| forecast.csv | 7fcc380165ce67eb8b5be94acf37516a209fcac061402890933db4576bf97c7f | 7fcc380165ce67eb8b5be94acf37516a209fcac061402890933db4576bf97c7f | 1200/1200 |
| gap_actions.csv | ef1031b567fcb2698a0184a94ec86e47e4d1fe48448bee6fa4a0e519d811ed1f | ef1031b567fcb2698a0184a94ec86e47e4d1fe48448bee6fa4a0e519d811ed1f | 2151/2151 |
| gap_actions.json | 6ba3bf72960743cec1705f093524e5ae53c176c4ae40ae6c7a45f969df22ab34 | 6ba3bf72960743cec1705f093524e5ae53c176c4ae40ae6c7a45f969df22ab34 | - |
| gap_analysis.csv | 164f737115ba4eb0794a73dc21f4bfbf518eaf0b3cf2ef4a4728c33b614fe0f4 | 164f737115ba4eb0794a73dc21f4bfbf518eaf0b3cf2ef4a4728c33b614fe0f4 | 4389/4389 |
| gap_analysis.json | 7fb2e5e8de91168ba5877266749a60cdeac89648138a902caaccb1a363253c6a | 7fb2e5e8de91168ba5877266749a60cdeac89648138a902caaccb1a363253c6a | - |
| ground_truth/ground_truth.csv | 715434d343b8a225585a75432eba2afbb702d3f252c337d1936d5bc21005b79e | 715434d343b8a225585a75432eba2afbb702d3f252c337d1936d5bc21005b79e | 404/404 |
| ground_truth/ground_truth.json | ecd8c9ff41351a122ddc7cbd07e9be51919efe1036d44f23c97fc0b93957a4fa | ecd8c9ff41351a122ddc7cbd07e9be51919efe1036d44f23c97fc0b93957a4fa | - |
| holidays.csv | 5711c21093aebd2ba01b16b87b3aca0d47fb612f2c03dbe2d8d59dd75918fffe | 5711c21093aebd2ba01b16b87b3aca0d47fb612f2c03dbe2d8d59dd75918fffe | 6/6 |
| holidays.json | 28199297d67197d153827ef093f72abe36ced5ab463748e5b18410d584d720c7 | 28199297d67197d153827ef093f72abe36ced5ab463748e5b18410d584d720c7 | - |
| leave.csv | e1c69d3736f3517064fcff9d48ab3282dbda3f2394b3a62501aeb8bf79fb9565 | e1c69d3736f3517064fcff9d48ab3282dbda3f2394b3a62501aeb8bf79fb9565 | 12001/12001 |
| leave.json | fb769ebb9b1aa4675b97c296003b2f11c18d0f42a5ffd65360eabb0d10a21dcf | fb769ebb9b1aa4675b97c296003b2f11c18d0f42a5ffd65360eabb0d10a21dcf | - |
| lifecycle_events.csv | b2ac77789e8505ddd234cfca6b63620510cbc9d4f32f3bb9aefa7f0a5bba88e0 | b2ac77789e8505ddd234cfca6b63620510cbc9d4f32f3bb9aefa7f0a5bba88e0 | 19620/19620 |
| lifecycle_events.json | 1d3d636fb589efdaf48eeb9e95799f9607e51601944e217b579a0690df3c62e3 | 1d3d636fb589efdaf48eeb9e95799f9607e51601944e217b579a0690df3c62e3 | - |
| manifest.json | 2989dd9e0983d492e94421b62c38285287689b9ab69053a79ce7bb9e0bc95394 | 2989dd9e0983d492e94421b62c38285287689b9ab69053a79ce7bb9e0bc95394 | - |
| metrics.json | e2472eae1b71d0fe287f95ad8e88fb009c58cf42540b9f4aadb856206620c47a | e2472eae1b71d0fe287f95ad8e88fb009c58cf42540b9f4aadb856206620c47a | - |
| proficiency_scale.csv | 27f5db839505a2ac7d13362e70b6a530157958baa84a987c939f180b38d74221 | 27f5db839505a2ac7d13362e70b6a530157958baa84a987c939f180b38d74221 | 5/5 |
| proficiency_scale.json | 4db213c4d0a2ac1959d64f520c8eeb0f5ae1b4f7a2dc5c6dfd792848b58e242c | 4db213c4d0a2ac1959d64f520c8eeb0f5ae1b4f7a2dc5c6dfd792848b58e242c | - |
| projects.csv | e7dd97b39c0a09e8be9d74fdc41fad7c4f478b810d8c607bf30117d90413225b | e7dd97b39c0a09e8be9d74fdc41fad7c4f478b810d8c607bf30117d90413225b | 500/500 |
| projects.json | d9940e1a509ff47fb56df0df4e8c94f0392486c1ab130794c477d52d5e7eb735 | d9940e1a509ff47fb56df0df4e8c94f0392486c1ab130794c477d52d5e7eb735 | - |
| role_skills.csv | 0f637b732016376c3a22d0da7ed524b89ca990c4a0a384778445cd95da3208e5 | 0f637b732016376c3a22d0da7ed524b89ca990c4a0a384778445cd95da3208e5 | 191/191 |
| role_skills.json | c4f08257281474da69d261e01afc6925b0d86dd8a75107228818fc7b1635fca3 | c4f08257281474da69d261e01afc6925b0d86dd8a75107228818fc7b1635fca3 | - |
| roles.csv | 8b13b2267412a6e3d622d48548175b11030f297269dcf98f67d576f4fda1c71b | 8b13b2267412a6e3d622d48548175b11030f297269dcf98f67d576f4fda1c71b | 40/40 |
| roles.json | d495f704a6caa55db151278bc8c7db884e694fda1da3b4ed84db7b4eebfec918 | d495f704a6caa55db151278bc8c7db884e694fda1da3b4ed84db7b4eebfec918 | - |
| schema.sql | daa934d3e15d0a99bea78287b31aeaa2aecc55893f7718e2317e84ce4c79221b | daa934d3e15d0a99bea78287b31aeaa2aecc55893f7718e2317e84ce4c79221b | - |
| seed.sql | 702004992b86cb0502943d8d063cad5daa220f44f1d14b7b6755867fbd1a4a0f | 702004992b86cb0502943d8d063cad5daa220f44f1d14b7b6755867fbd1a4a0f | - |
| skills.csv | 4183c1b7d8ca1be88087d9f0609b309df7ff7ed7621fa464e5746e0e49a2b0ea | 4183c1b7d8ca1be88087d9f0609b309df7ff7ed7621fa464e5746e0e49a2b0ea | 300/300 |
| skills.json | 46baae039234910926f14bbec8a1d3f9f94f538727a3793ad6a4328eacb28a0f | 46baae039234910926f14bbec8a1d3f9f94f538727a3793ad6a4328eacb28a0f | - |
| supply.csv | 071e854af7421c009e3944271e5c059295641445e41da24794a4f79477f051b6 | 071e854af7421c009e3944271e5c059295641445e41da24794a4f79477f051b6 | 4389/4389 |
| supply.json | 0b94680b8ed5fe61fb7fe93450fc4caebc1f23068dfebe0c3d5e707b2923b678 | 0b94680b8ed5fe61fb7fe93450fc4caebc1f23068dfebe0c3d5e707b2923b678 | - |
| training.csv | 7aff9151e06d3334b744ebc8189ed8e5913df6b6b76ce5bafd88eb0206a4c865 | 7aff9151e06d3334b744ebc8189ed8e5913df6b6b76ce5bafd88eb0206a4c865 | 251/251 |
| training.json | 6f8e1866293f15713de71f215d74ba875dce4593a774dec6a8a398f3b36374da | 6f8e1866293f15713de71f215d74ba875dce4593a774dec6a8a398f3b36374da | - |
| utilization.csv | e1186bf6a0326801a60c5d53e6953f1171b4258cc4ce43a892574c0aaf96e95e | e1186bf6a0326801a60c5d53e6953f1171b4258cc4ce43a892574c0aaf96e95e | 265000/265000 |
| utilization.json | 4844bce40a3768071e48cb017ae6634d5a783d434ef9bbb2934fb7a01432d028 | 4844bce40a3768071e48cb017ae6634d5a783d434ef9bbb2934fb7a01432d028 | - |
| validation_report.json | 5a745631630d727b75a935821a467c64a59b53e605050f1b0e11ed5ac6380b86 | 5a745631630d727b75a935821a467c64a59b53e605050f1b0e11ed5ac6380b86 | - |

### Portability, hygiene, and remaining gaps

**Python-version command:** isolated `uv run --python 3.11.15 --locked wdf generate --scale starter --seed 20261022 --out output/portability-py311`, repeated with `3.14.7` in a separate `UV_PROJECT_ENVIRONMENT`. Reusing the active `.venv` for the first attempt failed with Windows `Access is denied`; the isolated retry completed successfully.

```text
Generated 47 artifacts in output/portability-py311; Validation: PASS
Generated 47 artifacts in output/portability-py314; Validation: PASS
Python versions: 3.11.15 / 3.14.7; identical artifact hash maps: True (47/47)
```

`uv lock --check` resolved 27 exact package versions; `requirements-lock.txt` has 26 exact dependency pins, with the only uv.lock-only entry being the local project itself. The starter-hash comparison passed across the two tested Python versions. The current content scan over `output/full` found no absolute paths or wall-clock timestamp strings. Secret/contact scans found no credential patterns, email addresses, or phone numbers; no tracked `.env`, key, or certificate files were found. `rg -n '52' wdf tests tools` found only the explicit `"2026W52"` boundary test in `tests/test_p5.py`; `rg -n 'TODO|FIXME' wdf tests tools` and `rg -n 'print\\(' wdf` found no matches. Other fixed evaluation horizons (4/8/12 weeks) are prescribed backtest values; generator rates and weekly hours are read from `config/default.yaml`.

**Fresh-clone quickstart:** pending final commit and literal README execution; results will be added below. Make is not installed locally, and remote GitHub Actions was not run, so neither the Make target nor hosted CI is claimed as passing.

**Final verdict:** PASS for final data checks, tests, lint, dependency lock, docs, and full-scale repro. Fresh-clone verification and final hygiene inventory remain to be recorded after committing this documentation and `docs/PROBLEM.md`.

**Fix commits:** performance fix `2dbdbfb`; item 9 audit/documentation commit to be recorded after commit.

## Final known gaps

| Gap | Evidence/status |
|---|---|
| Forecast output is role/week, not project/role/week | `wdf/forecast.py` does not retain `project_id`; project-level demand forecasting is incomplete. |
| Stale-skill injection uses an expired skill incorrectly marked `Current` | No separate stale-proficiency value is modeled. |
| One Active allocation remains on a Cancelled project | Deliberate exception fixture, not a production cancellation policy. |
| Public GitHub push is unverified | This local audit did not push to or verify a public repository. |
| GNU Make and remote GitHub Actions were not run locally | Make is unavailable; direct commands passed, but CI is not claimed. |
| Zero-availability target was unspecified | Current full result is 3.019% of employee-weeks. |
| Perfect detector metrics are synthetic-rule results | Three seeds have zero FP/FN because deterministic injection matches deterministic rules; this does not establish real-world accuracy. |
| CLI test coverage is 55% | One `CliRunner` smoke test covers `generate`; README commands are also exercised in the fresh-clone quickstart. |
