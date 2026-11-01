# Traceability

This matrix maps every nonblank line in `docs/PROBLEM.md` to implementation and evidence. Blank separator lines are omitted. Partial items are listed under Known gaps.

| Problem line(s) | Requirement | Implementation | Evidence / status |
|---|---|---|---|
| 1–2 | Read and satisfy the complete source statement | This complete line-referenced matrix | All substantive lines 4–55 are mapped below; gaps are explicit. |
| 4–5 | Forecast demand by role/project; identify skill gaps, utilization risks, and hiring/training options | `wdf/forecast.py`, `wdf/derived.py`, `wdf/exports.py`, `wdf/validate.py`, `tools/independent_check.py` | `forecast.csv` and `forecast_project.csv` include role/week and project/role/week forecasts; rolling-origin metrics and no-look-ahead tests cover both levels. Project sums reconcile to role forecasts in both validators. Gap/action records retain rules, assumptions, and trace IDs. |
| 7–8 | Working end-to-end solution with related entities, conditional rules, exception paths, traceability, and measurable output | `wdf/models.py`, `wdf/derived.py`, `wdf/pipeline.py`, `wdf/evaluate.py` | Pydantic entities and conditional actions; failed-training fallback and budget escalation; detector and forecast metrics. |
| 10–11 | Employee/candidate, manager, HR partner, IT/operations partner, system administrator | `wdf/derived.py` actor rules; `wdf/models.py` | Action owners are enum-validated; `tests/test_p3.py`. |
| 13 | Workflow ordering and rules | `wdf/masters.py`, `wdf/transactions.py`, `wdf/derived.py` | Generation builds masters before transactions, then derives capacity, utilization, gaps, and actions; `tests/test_p1.py`–`tests/test_p3.py`. |
| 14 | Generate/reference Employee, Role, Skill, EmployeeSkill, Project first | `wdf/masters.py`, `wdf/transactions.py` | `generate_sources` creates parent/master data before dependent records; tests in `tests/test_p1.py` and `tests/test_p2.py`. |
| 15 | Dependent transaction/event records use valid parent IDs | `wdf/transactions.py`, `wdf/exports.py`, `wdf/validate.py` | FK and parent-reference tests plus `tools/independent_check.py`. |
| 16 | Taxonomy/proficiency, employee profiles, demand, allocations/leave, capacity/utilization, gaps/actions | `wdf/masters.py`, `wdf/transactions.py`, `wdf/derived.py` | `tests/test_p1.py`–`tests/test_p3.py`; independent full-scale recomputation. |
| 17 | Persist state changes as events and retain history | `wdf/transactions.py`, `wdf/anomalies.py`, `wdf/validate.py`, `docs/ERD.md` | Lifecycle history/current-state tests and independent latest-event comparison. |
| 18 | Derive outcomes and ground-truth labels from documented rules | `wdf/anomalies.py`, `wdf/evaluate.py`, `docs/ASSUMPTIONS.md` | Seeded eligible-target selection, rule-based labels, and per-seed evaluation; `tests/test_p5.py` and `tests/test_p6.py`. |
| 20–21 | Core entities, PK/FK, cardinality, optionality, dates, states, bridges, valid joins, separate anomaly labels | `wdf/models.py`, `wdf/exports.py`, `wdf/validate.py`, `docs/ERD.md`, `tools/independent_check.py` | Dictionary covers 19 tables/126 fields; ERD covers bridge/cardinality/history; fresh SQLite `PRAGMA foreign_key_check`. LifecycleEvent's polymorphic entity reference is checked in code. Ground truth is exported separately. |
| 23–24 | Exact EMP/SKL/PRJ/DEM/ALLOC names, zero padding, immutable and consistent IDs | `wdf/ids.py`, `wdf/masters.py`, `wdf/transactions.py`, `wdf/validate.py` | ID regex and FK checks in `tests/test_p1.py`, `tests/test_p6.py`, and independent full check. |
| 26–27 | Data dictionary for the ten named entities with types, requiredness, values, units, uniqueness, validation | `wdf/models.py`, `wdf/dictionary.py`, `docs/DATA_DICTIONARY.md` | `tests/test_p8.py`; `tools/check_docs.py` compares all Pydantic fields. Dictionary also documents all exported tables. |
| 28 | Parent-before-child creation and required domain calculations | `wdf/masters.py`, `wdf/transactions.py`, `wdf/derived.py` | Generation ordering and derived-value tests; independent checks. |
| 29 | Deterministic, zero-padded IDs and exact references | `wdf/ids.py`, `wdf/validate.py`, `tools/independent_check.py` | Full regex/FK validation. |
| 30, 39 | 5,000 employees, 300 skills, 500 projects, 12 months; expiry, PT capacity, leave, overlap; fixed seed and scales | `config/scale_full.yaml`, `config/scale_starter.yaml`, `config/default.yaml`, `wdf/masters.py`, `wdf/transactions.py` | Full run and 53-week independent calendar/capacity checks; realism measures in `docs/SELF_AUDIT.md`. |
| 31, 42 | Four required anomaly cases: over-allocation, stale/current skill, duplicate demand, overlapping project assignment | `wdf/anomalies.py`, `wdf/detect.py`, `wdf/evaluate.py` | Four issue types, per-seed scores, programmatic hard negatives, `tests/test_p5.py` and `tests/test_p6.py`. The stale-skill wording mismatch is a known gap. |
| 32 | Derive totals, balances, scores, statuses, and dates from sources | `wdf/derived.py`, `wdf/validate.py`, `tools/independent_check.py` | Availability/utilization/gap recomputation and 1,000 stratified gap recomputations. |
| 33 | Separate `ground_truth.csv/json`; labels never enter detector features | `wdf/exports.py`, `wdf/pipeline.py`, `wdf/detect.py` | Source-only detector test deletes the ground-truth folder; source-field scan finds no label/injected-ID fields. |
| 34 | PK/FK/enums/dates/arithmetic/lifecycle/duplicate validation | `wdf/validate.py`, `tools/independent_check.py`, SQL schema | Full `wdf validate`, independent CSV audit, and fresh SQLite `PRAGMA foreign_key_check`. |
| 35 | CSV/JSON/SQL, README, schema/dictionary, commands/seed, source manifest, validation summary | `wdf/exports.py`, `README.md`, `docs/DATA_DICTIONARY.md`, `docs/SOURCE_MANIFEST.md`, `docs/VALIDATION_SUMMARY.md` | `tools/check_docs.py` verifies schema coverage and generated manifest checksums. |
| 36 | Same-seed row counts and checksums; different-seed change | `wdf/pipeline.py` (`run_repro`), `tests/test_p7.py` | Full-scale repro records A/B hashes for all 46 canonical artifacts, CSV row counts, logical DB hashes, and the changed-seed comparison. |
| 41–42 | Required edge cases and negative scenarios | `wdf/anomalies.py`, `wdf/transactions.py`, `tests/test_p5.py`, `tests/test_p6.py` | All four labeled anomaly families plus exact-capacity, expiry-date, adjacent-demand, and adjacent-allocation negative fixtures. |
| 44–45 | Capacity reconciliation; traceable skill gaps; leave/PT utilization; recommendations cite assumptions | `wdf/derived.py`, `wdf/models.py`, `tools/independent_check.py` | Capacity/utilization/gap recomputation and sampled source/action trace tables in `docs/SELF_AUDIT.md`; legal high utilization has a distinct risk band and traceable review action, covered by `tests/test_p3.py`. |
| 47–48(a) | Realistic distributions and meaningful variation | `config/default.yaml`, `wdf/masters.py`, `wdf/transactions.py` | Actual-versus-target measurements in `docs/SELF_AUDIT.md` section B/J. |
| 48(b) | Consistent IDs and valid joins | `wdf/ids.py`, `wdf/validate.py`, `tools/independent_check.py` | Full PK/FK/regex check. |
| 48(c) | Dependency and lifecycle consistency | `wdf/transactions.py`, `wdf/validate.py` | Lifecycle tests and full latest-state comparison. |
| 48(d) | Correct derived values and reconciliation | `wdf/derived.py`, `wdf/validate.py`, `tools/independent_check.py` | Full arithmetic and 1,000 stratified gap recomputations. |
| 48(e) | Normal, boundary, failure, exception coverage | `wdf/anomalies.py`, `wdf/transactions.py`, `wdf/derived.py` | Near-miss tests, training fallback, budget escalation, and cancellation exception; counts in `docs/SELF_AUDIT.md`. |
| 48(f) | Separate ground truth | `wdf/exports.py`, `wdf/detect.py`, `tests/test_p6.py` | Ground-truth isolation test and source-only detection. |
| 48(g) | Fixed-seed reproducibility, documentation, lawful provenance | `wdf/pipeline.py`, `docs/SOURCE_MANIFEST.md`, `tools/check_docs.py` | Full repro, docs checks, and synthetic-only source manifest. |
| 50–51 | Optional external data requires provenance/license; do not use unauthorized or personal data | `docs/SOURCE_MANIFEST.md`, synthetic-only generator | No external dataset is used; source manifest states records are synthetic. |
| 53–54 | Before submission, push to a public GitHub repository | Not established by local artifacts | **Known gap:** this audit did not push to or verify a public repository. |
| 55 | Include a README explaining how to run it | `README.md` | README quickstart was executed in a fresh clone. |

## Known gaps

- Lines 31 and 42 describe stale proficiency treated as current. The implemented case is an expired skill incorrectly marked `Current`; no separate stale-proficiency value is modeled.
- Line 54's public GitHub push was not performed or verified.
- The cancellation exception intentionally retains one Active allocation on a Cancelled project; this is a fixture, not a production cancellation policy.
