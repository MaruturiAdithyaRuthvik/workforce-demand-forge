# Traceability

| Requirement / acceptance criterion | Implementation | Proof |
|---|---|---|
| Synthetic-only data; no network or secrets | `wdf/masters.py`, `wdf/transactions.py`, `docs/SOURCE_MANIFEST.md` | `tests/test_p2.py` |
| Fixed 2026 AS_OF and 53 ISO weeks, W53 boundary | `wdf/calendar.py`, `config/default.yaml` | `tests/test_p1.py`, `tests/test_p5.py` |
| Stable IDs, independent seeded entity streams, starter/full scale | `wdf/ids.py`, `wdf/masters.py`, `config/scale_*.yaml` | `tests/test_p1.py`, `tests/test_p7.py` |
| Role, skill, employee, project, skill bridge and proficiency masters | `wdf/masters.py`, `wdf/models.py` | `tests/test_p1.py` |
| Demand headers/lines, append-only revisions, leave, holiday, allocations, training, events | `wdf/transactions.py` | `tests/test_p2.py` |
| Append-only lifecycle history equals current status; legal transitions | `wdf/transactions.py`, `wdf/anomalies.py`, `wdf/validate.py` | `tests/test_p2.py`, `tests/test_p6.py` |
| Availability reconciles capacity, leave, holidays, part-time, and zero availability | `wdf/derived.py` | `tests/test_p3.py`, `tests/test_p5.py`, `tests/test_p6.py` |
| Utilization denominators, including leave and part-time availability | `wdf/derived.py` | `tests/test_p3.py`, `tests/test_p5.py` |
| Demand/supply/gaps and source trace IDs | `wdf/derived.py`, `wdf/pipeline.py` | `tests/test_p3.py`, `tests/test_p6.py` |
| Gap and utilization-risk recommendations cite rule IDs, actors, lead time, cost, assumptions, and source rows | `wdf/derived.py`, `wdf/models.py`, `wdf/exports.py` | `tests/test_p3.py`, `tools/independent_check.py` |
| Forecast after AS_OF; rolling origins and created-on cutoff | `wdf/forecast.py` | `tests/test_p4.py` |
| Four anomaly families, hard negatives, labels isolated to ground-truth exports | `wdf/anomalies.py`, `wdf/detect.py`, `wdf/exports.py` | `tests/test_p5.py`, `tests/test_p6.py` |
| Validator checks PK/FK/enums/IDs/dates/lifecycle/capacity/derived values | `wdf/validate.py`, `wdf/exports.py` | `tests/test_p6.py`, `tests/test_p7.py` |
| Main and held-out seed detection evaluation | `wdf/pipeline.py`, `wdf/evaluate.py` | `tests/test_p6.py`; `output/starter/metrics.json` |
| CSV/JSON exports, SQLite, SQL, manifest, and reproducibility hashes | `wdf/exports.py`, `wdf/pipeline.py` | `tests/test_p7.py`; `wdf repro` |
| Data dictionary generated from Pydantic schema | `wdf/models.py`, `wdf/dictionary.py`, `scripts/update_data_dictionary.py` | `tests/test_p8.py` |
| Reallocate/Contract actions escalate when contract cost exceeds configured budget | `wdf/derived.py`, `config/default.yaml` | `tests/test_p3.py` |

## Known gaps

- `docs/PROBLEM.md` is not present in the repository or its Git history. The rows above map the requirements represented in the available project files, but cannot certify a line-by-line mapping of the original ten steps, edge cases, and acceptance criteria. Restore the source specification before claiming complete traceability.
- A deliberate cancellation fixture keeps one Active allocation on a Cancelled project to exercise the required exception path; it is not evidence that production cancellation processing should leave allocations open.
