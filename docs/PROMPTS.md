# Prompt history


### 1. Core build

ROLE
You are a senior data engineer producing a hiring-assessment submission for YottaFlex AI. Build a SYNTHETIC DATA GENERATOR + VALIDATOR + RULE-BASED ANOMALY DETECTOR + DEMAND FORECAST for workforce planning (forecast demand by role/project; find skill gaps, utilization risks, hiring/training options). This is NOT a web app. Do not build any UI in this run.

RULES OF ENGAGEMENT
- Work through the phases below in order. After each phase: run tests, fix failures, then make a conventional commit (feat:, test:, docs:). Do not skip ahead.
- Never invent results. Every number in the docs must be pasted from a real run. If something does not work, record it in docs/LIMITATIONS.md.
- Do not ask me questions. Put assumptions in docs/ASSUMPTIONS.md.
- No network at runtime, no secrets, no external datasets, no real-looking personal data (emails use @example.invalid, no real names).

PHASES
P0 scaffold + spec docs | P1 config, calendar, ids, masters | P2 transactions + events | P3 derived layer + actions | P4 forecast | P5 anomalies + ground truth | P6 validate + detect + evaluate | P7 export + repro | P8 docs + traceability + final run

STACK
Python 3.11+, numpy (default_rng), pandas, pydantic v2, pyyaml, typer, pytest, ruff, SQLite (stdlib). Pin exact versions in pyproject.toml plus a lock file. Makefile for workflows. Must run on Windows/macOS/Linux.

CALENDAR
- AS_OF = 2026-10-22 (ISO 2026W43), fixed in config. Never use the wall clock.
- Horizon = every ISO week of 2026, derived with datetime.date.fromisocalendar. 2026 has 53 ISO weeks (W53 starts 2026-12-28): never hardcode 52. Treat W53 as a documented boundary case.
- Weeks <= W43 are history; later weeks are the forecast horizon.

DETERMINISM
- Seed 20261022 from config. One SeedSequence, spawn a child stream per entity so adding a table does not shift others.
- Scale is parameterized. config/scale_starter.yaml (e.g. 300 employees/60 skills/30 projects) and scale_full.yaml (5000/300/500) use the same code path.
- No unordered iteration affecting output, no uuid. Sort every table by PK. Fixed "\n" line endings, fixed float formatting, JSON with sort_keys. No timestamps inside hashed files.

IDS (zero-padded, immutable, exact across files)
EMP-000001; SKL-000001; PRJ-2026-000001; DEM-<project-id>-2026W01 (e.g. DEM-PRJ-2026-000001-2026W01); ALLOC-2026-000001.
Same style for the rest: ROLE-0001, ESK-000001, AVL-000001, LEAVE-000001, TRN-000001, GAP-2026W01-000001, GACT-000001, DEML-000001, EVT-000001.

ENTITIES (masters first, then children; every FK valid)
- Role (~40 across families Engineering, Data, QA, Design, PM, DevOps, Security, Support). Skill (300; category; validity_months for expiry). ProficiencyScale (1-5 with definitions). RoleSkill bridge (min_proficiency, importance).
- Employee (5,000; FT/PT; fte in {1.0, 0.8, 0.6, 0.5}; ~30% PT; hire_date; role_id; manager_id self-FK; lifecycle status with effective dates).
- Project (500; start/end; priority; staffing_model in {Shared-Pool, Dedicated-Team}; lifecycle Planned->Active->Completed|Cancelled).
- EmployeeSkill (N:M bridge): proficiency 1-5, last_verified_date, expiry_date = last_verified + validity_months, and currency_flag in {Current, Stale} = what the source system recorded. In the baseline, currency_flag always agrees with (expiry_date >= AS_OF). True staleness is always recomputable from expiry_date, so a wrong flag is detectable.
- DemandPlan = header (demand_id = DEM-<project>-2026Wnn, project_id, iso_week, week_start) + DemandLine (PK demand_line_id; demand_id FK; role_id FK; skill_id FK; required_fte; min_proficiency; source in {PlanTool, ResourceRequest}; created_on; supersedes_line_id nullable; status Draft/Approved/Superseded). Revisions are appended and the old line becomes Superseded; never overwrite. In the baseline, (demand_id, role_id, skill_id) is unique among Approved lines. The header+lines split is the one deliberate deviation from the brief (a DEM id is per project-week, demand is per role/skill). Document it in DESIGN_DECISIONS.md.
- Leave records (employee, start, end, type, status) with seasonal peaks; holidays from a fixed config calendar.
- Availability per employee-week, derived from Leave + holidays: capacity_hours = 40*fte; leave_hours; holiday_hours; available_hours = capacity - leave - holiday (>= 0).
- Allocation: employee, project, role, start, end, allocation_pct (percent of THAT WEEK's available_hours), skill_basis_esk_id (optional FK), lifecycle Proposed->Active->Completed|Cancelled. allocated_hours(week) = sum(pct * available_hours).
- Training: employee, skill, target_proficiency, cost, dates, lifecycle Planned->Enrolled->Completed|Failed|Cancelled.
- GapAnalysis: per week/role/skill. GapAction: 1:N child with candidate actions.
- LifecycleEvent: ONE append-only table (entity_type, entity_id, from_state, to_state, effective_date, reason) for Employee, Project, Allocation, Training, DemandLine. Current-state columns must equal the latest event.
- Distributions: Zipf skill popularity, log-normal project sizes, proficiency skewed to 2-3, stale rate ~12-18%, seasonal leave, ramp-up/ramp-down demand curves, some project-weeks with zero demand.

PIPELINE ORDER
1) build valid baseline sources; 2) inject labelled anomalies into SOURCE tables; 3) compute every derived table (Availability, utilization, supply, gaps, actions) from the post-injection sources using the same functions. Derived values therefore always reconcile arithmetically to sources, and anomalies are semantic errors, not arithmetic ones.

DERIVED RULES (all thresholds in config, no magic numbers)
- utilization_available = allocated_hours / available_hours; utilization_capacity = allocated_hours / capacity_hours. If available_hours = 0, utilization is null with flag ZERO_AVAILABILITY.
- supply_fte (role/skill/week) = sum(available_hours/40) of employees holding the skill at >= min_proficiency with currency_flag = Current.
- demand_fte = sum of Approved DemandLines. gap_fte = demand_fte - supply_fte. risk_level by config thresholds.
- Each GapAnalysis row stores source_demand_line_ids and supporting_esk_ids, so every gap traces back to demand and supply.
- GapAction rules: small gap + qualified-but-stale staff -> Reverify; medium gap + adjacent-skill staff -> Train; large persistent gap -> Hire; over-utilization -> Reallocate or Contract. Each action stores rule_id, owner_actor in {Employee, Manager, HR Partner, IT/Ops Partner, System Admin}, status Proposed->Approved->InProgress->Done|Rejected|Escalated, lead_time_weeks, estimated_cost, and an assumptions text citing rule_id and thresholds.
- Actors: Employee accepts training/reverification; Manager approves allocation and training; HR Partner approves hires; IT/Ops Partner owns access/provisioning lead time; System Admin owns data-quality corrections.
- Exception paths that must exist in the data: Hire over the config headcount budget -> Escalated to HR Partner; Train blocked after a Failed training for the same employee+skill -> falls back to Hire; project Cancelled with open allocations -> allocations closed via events and gaps recomputed; training Failed -> gap persists.

FORECAST (forecast.py)
Role-level weekly demand FTE for weeks after AS_OF. Method 1: seasonal-naive/moving-average baseline from past Approved demand. Method 2: pipeline-adjusted, with plan lines weighted by a documented confidence factor per project lifecycle state. Rolling-origin backtest on weeks <= W43 at 4/8/12-week horizons using ONLY lines with created_on <= origin date (no look-ahead). Report WAPE and bias per method; compare honestly even if method 2 loses. Output output/forecast.csv and output/metrics.json.

ANOMALIES (inject only after a fully valid baseline; ~1-3%, configurable; only target rows modified)
a) ALLOC_EXCEEDS_AVAILABILITY: weekly sum(allocation_pct) > 100 across Shared-Pool allocations (so allocated_hours > available_hours).
b) STALE_SKILL_TREATED_CURRENT, with subtype FLAG_WRONG (currency_flag=Current although expiry_date < AS_OF) or USED_WHILE_STALE (allocation justified by a skill_basis_esk_id that is stale at allocation start).
c) DEMAND_DOUBLE_COUNTED: a second Approved DemandLine with the same (demand_id, role_id, skill_id), no supersedes link, source=ResourceRequest.
d) OVERLAPPING_PROJECT_ASSIGNMENT: an employee on a Dedicated-Team project who also has an overlapping allocation elsewhere, with weekly sum(pct) <= 100 so it is not also type (a).
HARD NEGATIVES that the baseline must legitimately contain: overlapping Shared-Pool allocations summing <= 100%; Superseded revision pairs; stale skills correctly flagged Stale. Also include boundary cases: expiry_date exactly AS_OF (still current), zero-availability week, 100%-leave week, part-timer at exactly 100% of available hours, W53, project cancelled mid-flight.
Ground truth goes ONLY to output/ground_truth/ground_truth.csv and .json: record_id, entity, issue_type, issue_subtype, injected_field, original_value, injected_value, expected_detection_rule, expected_decision, affected_derived_ids. No label or ID list may appear in any input table.
SQL: PK/FK/CHECK only. Do NOT put UNIQUE on the demand business key (injected duplicates must load); validate.py checks it instead.

DETECTOR + EVALUATION
detect.py finds all four types using ONLY input tables and rules. It must not import or read ground truth. evaluate.py compares to ground truth: precision, recall, F1 per issue_type plus a cross-type confusion summary. Run on the main seed AND a second held-out seed to show the rules are not tuned to one dataset. Target >= 0.95; if lower, report the real numbers and explain. Write docs/VALIDATION_SUMMARY.md and output/metrics.json.

VALIDATION (validate.py: nonzero exit on failure, writes validation_report.json)
PK uniqueness; FK integrity for every relationship, also by loading seed.sql into SQLite with PRAGMA foreign_keys=ON; allowed enums; ID regex per entity; date ordering; lifecycle transition legality; capacity reconciliation by period (sum of employee availability = reported capacity for every week); utilization and gap recomputed from sources equal stored values; event history = current state; duplicate checks.

REPRODUCIBILITY (wdf repro)
Generate twice with the same seed into two dirs; compare row counts and SHA-256 of every CSV/JSON/SQL file and of the SQLite logical dump (not raw .db bytes). Also prove a different seed gives different hashes. Write output/repro_report.json including python/numpy/pandas versions; fail on mismatch. Note in LIMITATIONS.md that NumPy Generator streams are only guaranteed stable for a pinned version.

EXPORTS
CSV and JSON per table; schema.sql + seed.sql; workforce.db; manifest.json (file, rows, sha256, generator version, seed, command, scale); SOURCE_MANIFEST.md (no external data, fully synthetic).

CLI / MAKE
wdf generate --scale full --seed 20261022 --out output/ ; wdf validate | detect | evaluate | forecast | repro
make setup | starter | full | validate | test | repro | all | clean

TESTS (pytest, fast at starter scale)
ID formats; determinism; seed sensitivity; FK integrity; reconciliation; each anomaly type injected AND detected; hard negatives not flagged; ground-truth non-leakage into inputs; lifecycle legality; boundary cases; forecast no-look-ahead (mutate lines with created_on > origin, forecast unchanged).

DOCS (real content, no placeholders)
README (what/why, 5-command quickstart, expected output, folder map, how to verify, environment needs, runtime target <2 min for full, limitations). DATA_DICTIONARY.md for EVERY field of EVERY table (type, required/optional, allowed values, units, uniqueness, validation rule), generated from the pydantic schemas so doc and code cannot drift. ERD.md (mermaid; cardinalities 1:1/1:N/N:M, optional relations, effective dates, lifecycle state diagrams). ASSUMPTIONS.md, DESIGN_DECISIONS.md, LIMITATIONS.md. AI_USAGE.md as a template with clearly marked blanks for ME to fill truthfully. TRACEABILITY.md mapping every line of the problem statement and each acceptance criterion (capacity reconciles by period; skill gaps traceable to demand; utilization includes leave/part-time; recommendations cite assumptions) to the file/test that proves it.

FINISH
Run make all and make repro. Paste real results (row counts, validation, per-type P/R/F1 on both seeds, forecast WAPE, repro result) into the README. Commit only the starter sample output; gitignore the rest.

### 2. Evidence audit

ROLE
You are an adversarial QA engineer. Phases P0-P8 are reported complete. Assume NOTHING is proven until you show command output. Goal: produce evidence, find defects, fix root causes.

RULES
- Every claim in the docs must be backed by a command you ran in this session. Paste the command and key output lines into docs/SELF_AUDIT.md.
- If a check fails, fix the generator or code. NEVER weaken a test, threshold or validation rule to make it pass. If you change one for a legitimate reason, justify it in SELF_AUDIT.md.
- Do not edit docs/AI_USAGE.md or prompts/. Do not rewrite git history. Make small conventional commits for fixes.

A. FULL SCALE
1. Run the full pipeline at scale_full (5,000 employees, 300 skills, 500 projects, all ISO weeks of 2026). Record wall-clock time and peak memory. Print row counts for every table.
2. Confirm 53 ISO weeks (2026W01..2026W53), exact ID formats (EMP-000001, SKL-000001, PRJ-2026-000001, DEM-<project-id>-2026Wnn, ALLOC-2026-000001), ~40 roles.
3. If runtime exceeds 3 minutes or memory is excessive, profile and vectorize.

B. DATA REALISM (print actual vs target in a table; fix misses)
Part-time share ~30%; stale-skill rate 12-18%; proficiency skewed to 2-3; heavy-tailed skill popularity; spread of project sizes; leave by month (seasonality); share of employee-weeks with zero availability; anomaly rate per type (1-3%); counts of hard negatives and boundary cases per type.

C. INDEPENDENT INTEGRITY CHECK
Write tools/independent_check.py using ONLY the stdlib (csv, sqlite3, datetime, re). It must import nothing from src/wdf. From the exported files verify: PK uniqueness; every FK; enums; ID regexes; date ordering; available = capacity - leave - holiday; capacity reconciliation by week; utilization recompute; gap = demand - supply recompute on >= 1,000 sampled rows; LifecycleEvent latest state = current state; the only duplicate Approved (demand_id, role_id, skill_id) lines equal the injected double-count anomalies. Load seed.sql into a fresh SQLite with PRAGMA foreign_keys=ON and run PRAGMA foreign_key_check. Exit nonzero on failure. Add `make independent-check`.

D. TRACEABILITY SPOT CHECK
- Sample 25 random GapAnalysis rows. For each, resolve source_demand_line_ids to real lines, resolve supporting_esk_ids to real non-stale EmployeeSkill rows meeting min proficiency, and show linked GapAction rows with rule_id, owner_actor and assumptions text.
- Show 5 examples where utilization_capacity differs from utilization_available because of leave or fte.
- Show every exception path exists in the data (budget escalation, failed-training fallback to Hire, cancelled project with open allocations), with counts and example IDs.

E. ANOMALY + DETECTOR HONESTY
1. Prove detect.py never reads ground truth: grep imports and paths; add a test that deletes the ground_truth folder and still runs detect.
2. Prove no leakage: no issue_type or ground-truth columns and no injected-ID lists in input tables.
3. Report per issue_type: injected, detected, TP, FP, FN, precision, recall, F1 on the main seed AND two other held-out seeds. List up to 5 real false positives and 5 false negatives with reasons. Report hard-negative counts and show none were flagged. If any metric is 1.00, explain why that is plausible.
4. Confirm types do not interfere: injection (d) never also trips (a); records overlap across types only where labelled.

F. FORECAST
Show the backtest table (4/8/12-week horizons, both methods, WAPE and bias). Show the no-look-ahead test passing. State honestly which method wins and where it fails.

G. REPRODUCIBILITY
Run `wdf repro` at FULL scale. Show matching row counts and SHA-256 for every file across two runs, and different hashes for a different seed. Show pinned versions recorded. Confirm no timestamps or absolute paths inside hashed files.

H. REPO HYGIENE
grep for hardcoded 52, magic numbers in src/, TODO/FIXME, debug prints. Secret scan (keys, tokens, .env) and no real-looking personal data. List repo size and any committed file > 5 MB. Confirm uv.lock / requirements-lock.txt pin exact versions of ALL dependencies including transitive. Fresh-clone test: git clone into a temp dir, follow the README quickstart literally in a clean virtualenv, report any failing step or undocumented prerequisite. Run ruff, pytest (with coverage summary), and `uv lock --check`.

I. DOCS COMPLETENESS
- Write tools/check_docs.py comparing every field of every table in the pydantic schemas to docs/DATA_DICTIONARY.md; fail if any field is missing.
- Check SOURCE_MANIFEST.md (states no external data) and that manifest.json checksums match the actual files.
- README numbers must exactly match fresh command output; fix mismatches.
- TRACEABILITY.md must map every line of docs/PROBLEM.md (steps 1-10, edge cases, acceptance criteria) to a file or test. List partial items under "Known gaps"; do not hide them.
- LIMITATIONS.md must include the real limitations found in this audit.

DELIVERABLE
docs/SELF_AUDIT.md with sections A-I, each showing command, key output, verdict PASS/FAIL/FIXED, and the fix commit hash. End with a table of remaining known gaps. Then summarize findings in under 15 lines.

### 3. Hardening round 2

CONTEXT
P0-P8 and the Prompt 4 audit are done. docs/PROBLEM.md now exists (the original problem statement). This round fixes weaknesses found in review. Same rules as before: evidence for every claim, never weaken a test or threshold to make it pass, no edits to docs/AI_USAGE.md or prompts/, no git history rewrite. Commit after each numbered item. If tests fail, fix the cause before continuing.

0. MEASURE FIRST (print into docs/SELF_AUDIT.md section J, before any change)
- allocations per employee: distribution, share of employees with 2+ allocations, share with overlapping date ranges
- share of employees with >=1 leave record; leave starts per month; average leave days per employee; share of employee-weeks with zero availability
- GapAction counts by action_type and rule_id; number of over-utilized employee-weeks and how many have an action
- share of forecasts below actual, per method

1. ALLOCATION REALISM
The baseline must contain realistic multi-allocation staffing: sequential allocations over the year, part-year allocations, and concurrent Shared-Pool allocations summing <= 100% of available hours. Put targets in config (e.g. total allocations >= 1.5x employees; 15-25% of employees with legal overlapping allocations). Dedicated-Team members must have NO overlapping allocation in the baseline. Keep injected anomaly rates at 1-3% of eligible records. Invariants for anomaly types (a)-(d) must still hold.

2. LEAVE REALISM
Most employees (e.g. 70-90%) have at least one leave record. Spread leave across all months with summer and December peaks, a mix of short and week-long leave, and enough full-week leave that zero-availability weeks are a few percent of employee-weeks. Leave must feed Availability exactly as before.

3. DEMAND CURVES
Add ramp-up / steady / ramp-down demand profiles per project (config-driven). Keep the zero-demand weeks and the Superseded revision mechanism.

4. UTILIZATION-RISK ACTIONS
Emit Reallocate and Contract actions for over-utilization using config thresholds, with owner_actor, rule_id, assumptions text and traceable source IDs. Add one exception path for them (e.g. Contract over the budget cap -> Escalated). Update docs and tests.

5. FORECAST
Investigate why pipeline-adjusted bias equals -WAPE at every horizon and explain it in DESIGN_DECISIONS.md. Add method 3: pipeline-adjusted with a realization ratio learned ONLY from data before each backtest origin. Keep the no-look-ahead test and extend it to method 3. Report all three methods honestly across 4/8/12-week horizons and several origins.

6. DETECTOR CREDIBILITY
Add programmatic near-miss hard negatives per issue type (e.g. allocation sum exactly 100%, expiry exactly on the as-of date, shared overlaps summing exactly 100%, Dedicated-Team allocations that are adjacent but not overlapping, same role/skill in adjacent weeks). Report counts per type. The detector must flag none of them. Do not tune detector rules using ground truth.

7. PORTABILITY AND REPRODUCIBILITY
- Add .gitattributes forcing LF line endings for generated CSV/JSON/SQL so checksums survive checkout on any OS.
- Verify the starter manifest hashes are identical under Python 3.11 and the Python version used for the full run (uv run --python <version>). If they differ, fix the cause (float formatting, ordering) or document exactly which versions are guaranteed.
- Add .github/workflows/ci.yml for ubuntu-latest: uv sync --locked, make starter, make validate, make test, make independent-check, make repro (starter scale). Fix any Makefile problem it reveals. If you cannot run CI locally, say so in SELF_AUDIT.md instead of claiming it passes.

8. CONFIG AND TESTS
Move magic numbers (anomaly allocation factor, demand omission rate, leave chance, weekly hours, etc.) into config/default.yaml and read them from code. Add pytest-cov to dev dependencies so `make test` prints a coverage summary. Add a CLI smoke test using Typer's CliRunner.

9. FINAL RE-RUN
Re-run and show output for: full generate with timing, independent check, validate, detect + evaluate on the main seed and two held-out seeds, forecast, repro at full scale, docs checks, fresh-clone quickstart. Complete docs/TRACEABILITY.md line by line against docs/PROBLEM.md (steps 1-10, edge cases, acceptance criteria, evaluation focus a-g). Update README numbers to match fresh output. Add section J (this round) to SELF_AUDIT.md with before/after tables and list remaining gaps honestly. Commit.


### 5. Final fixes (lite)

CONTEXT
Hardening round 2 is done. Same rules: evidence for every claim, never weaken a test or threshold, do not edit docs/AI_USAGE.md or prompts/, no git history rewrite, no subagents. Do not ask me questions. Work at STARTER scale while developing; run full scale only once, in item 4. Commit after each item.

1. PROJECT-LEVEL FORECAST (the brief says "forecast demand by role/project")
Add a project/role/week forecast as a new output (e.g. forecast_project.csv: project_id, role_id, iso_week, method, predicted_fte). Keep the role-level forecast. Backtest at project/role/week level using only data available before each origin; report WAPE and bias honestly (expect worse than role level). Reconciliation: project-level predictions summed over projects must equal the role-level prediction for the same method, role and week (or document exactly why not). Add this check to validate.py AND tools/independent_check.py. Update the data dictionary, ERD, TRACEABILITY and tests, including a no-look-ahead test.

2. VALIDATION WARNINGS
Print the 2 current validation warnings with exact text. Fix their cause, or document why they are expected in README and docs/LIMITATIONS.md.

3. UTILIZATION RISK (measure first)
Report how many over-utilized employee-weeks come from baseline data versus injected anomaly type (a). Only if more than 80% come from injection: add a legal "high utilization" band (config threshold, e.g. 0.9 <= utilization_available <= 1.0) that creates risk levels and actions without being an anomaly. Either way, document in DESIGN_DECISIONS.md why both Reallocate and Contract are emitted per over-utilized week, or make Contract conditional via a config rule. Anomaly detection results must not change.

4. FINAL VERIFICATION (run once, show output)
Full-scale generate with timing, validate, tools/independent_check.py, detect + evaluate on the main seed, forecast (both levels), repro at full scale, pytest with coverage, ruff, uv lock --check, one fresh-clone quickstart. Run the 3-seed detector evaluation only if generation code changed in item 3. Update README numbers to match fresh output. Add section K to docs/SELF_AUDIT.md (short, with before/after for items 1-3). Update docs/TRACEABILITY.md. Commit, then create git tag v1-core.

