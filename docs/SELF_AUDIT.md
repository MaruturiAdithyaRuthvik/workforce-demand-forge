# Adversarial self-audit

Audit run on 2026-11-01 against seed `20261022` on Windows. Commands and outputs below are from this session. `N/A` means the section found no code defect requiring a fix; commit hashes identify the commits that repaired discovered issues.

## A. Full scale

**Command:** `uv run wdf generate --scale full --seed 20261022 --out output/full` (run under a PowerShell process-tree working-set sampler at 250 ms intervals).

**Key output:**

```text
Generated 47 artifacts in output\full
Validation: PASS
WALL_SECONDS=70.495 PEAK_TREE_WORKING_SET_MB=720.1
```

`config/scale_full.yaml` reports employees `5000`, skills `300`, projects `500`, roles `40`. `uv run python tools/independent_check.py output/full` verified all 53 weeks `2026W01`–`2026W53`, every ID regex, and the counts below. The sampled IDs were `EMP-000001`, `SKL-000083`, `PRJ-2026-000001`, `DEM-PRJ-2026-000001-2026W41`, and `ALLOC-2026-000001`.

| Table | Rows |
|---|---:|
| roles | 40 |
| skills | 300 |
| proficiency_scale | 5 |
| role_skills | 191 |
| employees | 5,000 |
| employee_skills | 57,595 |
| projects | 500 |
| demand_plans | 4,024 |
| demand_lines | 6,193 |
| leave | 651 |
| holidays | 6 |
| allocations | 5,025 |
| training | 251 |
| lifecycle_events | 17,002 |
| availability | 265,000 |
| utilization | 265,000 |
| supply | 4,316 |
| gap_analysis | 4,316 |
| gap_actions | 1,939 |

**Verdict:** PASS. Runtime is below the 180-second trigger; the sampled process-tree peak was about 720 MiB. No profiling/vectorization was needed. Sampling can miss a sub-250-ms peak.

**Fix commit:** N/A.

## B. Data realism

**Command:** `uv run python -` (seeded calculations over the freshly generated `output/full/*.json`; seed `20261022`).

| Measure | Target used for this audit | Actual | Verdict |
|---|---:|---:|---|
| Part-time employee share | approximately 30% (25–35% audit band) | 31.380% (1,569/5,000) | PASS |
| Expired skill rate | 12–18% | 15.055% (8,671/57,595) | PASS |
| Proficiency levels 2–3 | majority | 68.193%; counts 1: 2,910; 2: 17,343; 3: 21,933; 4: 11,388; 5: 4,021 | PASS |
| Skill popularity | heavy-tailed; max at least 3× median and top 10 exceed 10% | min 97; median 142.5; p90 295; max 1,988; top-10 share 15.87% | PASS after fix |
| Project allocation/team sizes | visible spread | min 1; median 7; p90 22; max 60; zero projects 0 | PASS after fix |
| Leave seasonality | seasonal concentration visible | 651 leave rows; starts: Feb 145, May 161, Jul 178, Dec 167 | PASS |
| Employee-weeks with zero availability | report; no numeric threshold specified | 131/265,000 (0.049%) | Reported; sparse |
| Injected anomaly rate per eligible population | 1–3% | see type table below | PASS |

| Issue type | Injected | Eligible denominator | Actual rate |
|---|---:|---:|---:|
| ALLOC_EXCEEDS_AVAILABILITY | 77 | 3,863 Shared-Pool allocations | 1.993% |
| STALE_SKILL_TREATED_CURRENT | 173 | 8,671 expired employee skills | 1.995% |
| DEMAND_DOUBLE_COUNTED | 121 | 6,168 Approved demand lines | 1.962% |
| OVERLAPPING_PROJECT_ASSIGNMENT | 23 | 1,162 eligible Dedicated-Team allocations | 1.979% |

The original uniform skill assignment and round-robin project staffing produced a nearly uniform skill count (185–240) and almost identical project sizes (median 10, p90 10). Skill selection now uses seeded power-law weights and project assignment uses seeded log-normal weights with a one-project minimum where possible. New measurable tests exercise both distributions. The revised full run measured max/median skill popularity 13.95× and project p90/median 3.14×.

**Verdict:** FIXED. The zero-availability share is measured but was not assigned a target in the request; it remains a realism limitation, not a threshold failure.

**Fix commit:** `788ddfe`.

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

**Command:** `uv run python -` with `random.Random(20261101).sample(gap_rows, 25)`. For every sampled row, the check resolved every demand-line ID, resolved every supporting EmployeeSkill ID, and asserted matching role/skill, `Current` flag, expiry on/after `2026-10-22`, and proficiency at least the minimum approved-line requirement.

**Key output:** `25 of 4316 GapAnalysis rows`; `Resolved demand lines: 37/37`; `supporting skills passed current/expiry/proficiency/role/skill checks: 57/57`.

| Gap ID | Resolved demand lines | Valid supporting ESK | Linked action: ID / rule / owner / assumptions |
|---|---|---|---|
| GAP-2026W16-000746 | DEML-000404 | 7/7; ESK-018013, ESK-029082 | none |
| GAP-2026W19-000949 | DEML-001445, DEML-002371, DEML-002643, DEML-003584 | 0/0 | GACT-000322 / GAP_HIRE_LARGE / HR Partner / gap_fte=4.8318 >= medium_gap_fte=2.0 |
| GAP-2026W41-003229 | DEML-000148, DEML-000663, DEML-002887 | 4/4; ESK-012789, ESK-014045 | none |
| GAP-2026W13-000490 | DEML-005814 | 1/1; ESK-042207 | none |
| GAP-2026W11-000356 | DEML-005780 | 0/0 | GACT-000120 / GAP_TRAIN_MEDIUM / Manager / gap_fte=1.7052; adjacent skill SKL-000001; thresholds low=0.5, medium=2.0 |
| GAP-2026W12-000414 | DEML-003575 | 0/0 | GACT-000137 / GAP_TRAIN_MEDIUM / Manager / gap_fte=1.4961; adjacent skill SKL-000003; thresholds low=0.5, medium=2.0 |
| GAP-2026W27-001796 | DEML-002568, 002813 | 3/3; ESK-007161, ESK-014891 | none |
| GAP-2026W31-002251 | DEML-001050 | 4/4; ESK-015515, ESK-029522 | none |
| GAP-2026W36-002699 | DEML-000656 | 1/1; ESK-001979 | GACT-000960 / TRAIN_FAILED_FALLBACK / HR Partner / employee EMP-000003 failed skill SKL-000300; original rule GAP_TRAIN_MEDIUM |
| GAP-2026W19-001027 | DEML-003940 | 1/1; ESK-037232 | none |
| GAP-2026W21-001164 | DEML-000202, DEML-001446, DEML-005699 | 1/1; ESK-048119 | GACT-000399 / GAP_HIRE_LARGE / HR Partner / gap_fte=2.3284 >= medium_gap_fte=2.0 |
| GAP-2026W45-003658 | DEML-003993 | 2/2; ESK-000348, ESK-021883 | none |
| GAP-2026W49-004003 | DEML-004957 | 1/1; ESK-031186 | GACT-001426 / GAP_TRAIN_MEDIUM / Manager / gap_fte=1.1573; adjacent skill SKL-000022; thresholds low=0.5, medium=2.0 |
| GAP-2026W20-001117 | DEML-001983, DEML-002766 | 2/2; ESK-048543, ESK-053239 | none |
| GAP-2026W02-000012 | DEML-003138 | 3/3; ESK-001310, ESK-009773 | none |
| GAP-2026W37-002897 | DEML-003626 | 2/2; ESK-012146, ESK-023235 | none |
| GAP-2026W08-000216 | DEML-004011 | 1/1; ESK-009265 | none |
| GAP-2026W49-004029 | DEML-001437 | 1/1; ESK-051781 | none |
| GAP-2026W40-003179 | DEML-002692, 004663 | 2/2; ESK-039440, ESK-039873 | GACT-001135 / GAP_REVERIFY_SMALL / Employee / qualified stale skill; gap_fte=0.3650 < low_gap_fte=0.5 |
| GAP-2026W17-000847 | DEML-004282 | 1/1; ESK-053683 | GACT-000285 / GAP_TRAIN_MEDIUM / Manager / gap_fte=1.1175; adjacent skill SKL-000064; thresholds low=0.5, medium=2.0 |
| GAP-2026W50-004064 | DEML-002328 | 2/2; ESK-041514, ESK-044690 | none |
| GAP-2026W05-000056 | DEML-000122 | 1/1; ESK-001979 | GACT-000015 / TRAIN_FAILED_FALLBACK / HR Partner / employee EMP-000003 failed skill SKL-000300; original rule GAP_TRAIN_MEDIUM |
| GAP-2026W24-001528 | DEML-000061, DEML-005146 | 1/1; ESK-009265 | GACT-000538 / GAP_TRAIN_MEDIUM / Manager / gap_fte=1.4851; adjacent skill SKL-000213; thresholds low=0.5, medium=2.0 |
| GAP-2026W18-000893 | DEML-000551, DEML-005798 | 13/13; ESK-001031, ESK-010925 | none |
| GAP-2026W36-002704 | DEML-001890 | 3/3; ESK-000783, ESK-006529 | none |

Five utilization examples confirmed that leave/holiday hours change utilization-capacity versus utilization-available; one case is part-time:

| Employee | Week | FTE | Capacity h | Leave h | Holiday h | Utilization available | Utilization capacity |
|---|---|---:|---:|---:|---:|---:|---:|
| EMP-000031 | 2026W49 | 1.0 | 40.0 | 24.0 | 0.0 | 0.25 | 0.10 |
| EMP-000088 | 2026W49 | 1.0 | 40.0 | 8.0 | 0.0 | 0.25 | 0.20 |
| EMP-000117 | 2026W29 | 1.0 | 40.0 | 32.0 | 0.0 | 0.75 | 0.15 |
| EMP-000001 | 2026W48 | 1.0 | 40.0 | 0.0 | 8.0 | 0.85 | 0.68 |
| EMP-000003 | 2026W52 | 0.6 | 24.0 | 0.0 | 4.8 | 1.00 | 0.80 |

Exception fixtures and counts: 331 Escalated budget actions (example `GACT-000084`); 18 `TRAIN_FAILED_FALLBACK` Hire actions (example `GACT-000002`, with failed `TRN-000251` for `EMP-000003`/`SKL-000300`); one Cancelled project with one open Active allocation (`PRJ-2026-000008` / `ALLOC-2026-000068`).

**Verdict:** FIXED; all 25 selected trace chains resolved and the missing cancelled-project/open-allocation fixture was added.

**Fix commit:** `788ddfe`.

## E. Anomaly and detector honesty

**Commands:** `uv run wdf detect --input output/full`; `uv run wdf evaluate --input output/full`; a direct seeded evaluation of full-scale seed `20261024`; `rg -n 'ground_truth|ground truth|issue_type|injected' wdf/detect.py wdf/pipeline.py`; `uv run pytest -q tests/test_p6.py::test_detection_runs_without_ground_truth`.

The deletion test generated an output directory, removed its `ground_truth` folder, called `run_detection`, and passed. `wdf/detect.py` has no ground-truth path/import; `run_detection` now reads source tables only. `pipeline.py` reads ground truth only in evaluation/general validation loading paths.

| Seed | Issue type | Injected | Detected | TP | FP | FN | Precision | Recall | F1 |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 20261022 | ALLOC_EXCEEDS_AVAILABILITY | 77 | 77 | 77 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| 20261022 | DEMAND_DOUBLE_COUNTED | 121 | 121 | 121 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| 20261022 | OVERLAPPING_PROJECT_ASSIGNMENT | 23 | 23 | 23 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| 20261022 | STALE_SKILL_TREATED_CURRENT | 173 | 173 | 173 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| 20261023 | ALLOC_EXCEEDS_AVAILABILITY | 76 | 76 | 76 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| 20261023 | DEMAND_DOUBLE_COUNTED | 122 | 122 | 122 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| 20261023 | OVERLAPPING_PROJECT_ASSIGNMENT | 24 | 24 | 24 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| 20261023 | STALE_SKILL_TREATED_CURRENT | 168 | 168 | 168 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| 20261024 | ALLOC_EXCEEDS_AVAILABILITY | 75 | 75 | 75 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| 20261024 | DEMAND_DOUBLE_COUNTED | 121 | 121 | 121 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| 20261024 | OVERLAPPING_PROJECT_ASSIGNMENT | 25 | 25 | 25 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| 20261024 | STALE_SKILL_TREATED_CURRENT | 181 | 181 | 181 | 0 | 0 | 1.000 | 1.000 | 1.000 |

No false-positive or false-negative examples exist in these runs (all FP/FN counts are zero). A 1.000 score is plausible here because the injection mutates records to directly satisfy the same deterministic predicates used by the detector; it is not evidence of production accuracy. Main-seed GT had zero multi-type record IDs; seed `20261024` also had zero, and no injected type-(d) record was flagged as type-(a). A union-of-fields scan across all 637,354 source/derived rows found no `issue_type`, `ground_truth`, `injected_ids`, `affected_derived_ids`, `original_value`, `injected_value`, `expected_detection_rule`, or ground-truth `record_id` fields.

| Issue family | Hard negatives (count; none flagged) | Boundary fixtures (count; none flagged) |
|---|---|---|
| ALLOC_EXCEEDS_AVAILABILITY | 1 valid Shared-Pool overlap, `ALLOC-2026-005024` | 1 part-time 100%-allocation W52 boundary, `ALLOC-2026-005025` |
| STALE_SKILL_TREATED_CURRENT | 0 | 1 expiry exactly on as-of date, `ESK-000001` |
| DEMAND_DOUBLE_COUNTED | 25 valid Superseded demand revisions | 0 |
| OVERLAPPING_PROJECT_ASSIGNMENT | 1 valid Shared-Pool overlap, `ALLOC-2026-005024` | 0 |

One separate five-day leave boundary was present (`LEAVE-004987`, 2026-05-11 through 2026-05-15). Ground truth contains 77/173/121/23 labels by type and no IDs overlap between types.

**Verdict:** FIXED; detection no longer requires ground truth. Scores are exact on these generated seeds, with the synthetic-rule caveat above.

**Fix commit:** `f627ed5`.

## F. Forecast

**Commands:** `uv run wdf forecast --input output/full`; `uv run pytest -q tests/test_p4.py::test_backtest_pipeline_excludes_lines_created_after_origin tests/test_p6.py::test_detection_runs_without_ground_truth`.

| Method | Horizon (weeks) | WAPE | Bias |
|---|---:|---:|---:|
| 4-week moving average | 4 | 0.5451 | -0.0949 |
| 4-week moving average | 8 | 0.5566 | -0.1532 |
| 4-week moving average | 12 | 0.5629 | -0.2220 |
| Pipeline adjusted | 4 | 0.3766 | -0.3766 |
| Pipeline adjusted | 8 | 0.5264 | -0.5264 |
| Pipeline adjusted | 12 | 0.6498 | -0.6498 |

The no-look-ahead test passed (`2 passed`). Pipeline adjustment wins WAPE at 4 and 8 weeks, while moving average wins at 12 weeks. Both underforecast; pipeline adjustment has the more negative bias at every horizon.

**Verdict:** PASS; limits and horizon-dependent results are documented.

**Fix commit:** N/A.

## G. Reproducibility

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

## H. Repository hygiene

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

**Commands:** `uv run python tools/check_docs.py output/starter`; `uv run python tools/check_docs.py output/full`; `Test-Path docs\PROBLEM.md`; `git --no-pager log --all --oneline -- docs/PROBLEM.md`.

**Key output:**

```text
PASS data dictionary: 19 tables, 123 Pydantic fields
PASS SOURCE_MANIFEST.md states synthetic records and no external data
PASS manifest checksums and inventory: 49 files
docs\PROBLEM.md: False
No docs/PROBLEM.md commit in Git history
```

The source manifest and every manifest checksum were checked against generated files. README figures were reconciled to the fresh starter/full command outputs. The traceability file now surfaces rather than conceals the missing source specification and unimplemented behavior.

**Verdict:** FAIL for complete line-by-line traceability: `docs/PROBLEM.md` and its ten steps/edge cases/acceptance criteria are absent, so it is impossible to map its lines without inventing requirements. Available requirements remain mapped in `docs/TRACEABILITY.md`; see remaining gaps.

**Fix commit:** `42443cf` (automated field/checksum checker); documentation disclosure commit `a754da9`.

## Remaining known gaps

| Gap | Evidence/status |
|---|---|
| `docs/PROBLEM.md` absent; exact ten-step and acceptance-criteria traceability cannot be certified | Confirmed absent from working tree and Git history; restore it to complete the map |
| `Contract` action is allowed by schema but no Contract recommendation rule emits it | Source traceability gap documented in `docs/TRACEABILITY.md` |
| Explicit demand ramp-up/ramp-down curves are not modeled | Demand generation uses stochastic omissions/quantities; documented in traceability and limitations |
| Zero availability is rare (0.049%) | Measured; no target threshold was specified |
| Perfect detector metrics are generated-rule performance, not production evidence | No FP/FN in the three audited synthetic seeds; documented in README and limitations |
| One Active allocation remains on a Cancelled project by design | Intentional cancellation exception fixture; not a production cancellation policy |
| CLI unit-test coverage is 0% | Python CLI smoke workflows passed in the clean clone; coverage report is 89% overall |
| Make executable unavailable on this Windows machine | Make target exists; equivalent `uv run` command passed |

## J. Follow-up review baseline (measured before changes)

**Command:** `uv run python -` (stdlib calculations over `output/full/*.json`; forecast below-actual share recomputed over the existing rolling-origin forecasts using `wdf.forecast._predictions`).

**Key output:**

```text
allocations_per_employee distribution (allocations: employees): {1: 4975, 2: 25}
employees with 2+ allocations: 2/5000 = 0.040%
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

**Verdict:** Baseline captured before changes; deficiencies are the targets of items 1–8.

**Fix commit:** N/A (measurement only).
