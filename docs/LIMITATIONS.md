# Limitations

- All datasets, evaluation labels, and detector results are synthetic; they are not operational recommendations or evidence of real-world accuracy.
- Starter validation intentionally reports `11 approved demand business-key duplicate(s), surfaced for anomaly detection` and `6 employee skill currency flag(s) disagree with expiry and are detector cases`. These are the injected duplicate-demand and stale-skill/current-flag test cases; validation still reports zero structural errors. Warning counts scale with the generated dataset and seed.
- Project-level forecasts are allocated from historical project/role demand shares for the moving-average method and from visible pipeline lines for pipeline methods. This reconciles to role totals but does not model project-specific drivers beyond those observed lines and shares; project-level backtest errors are consequently worse in some method/horizon combinations.
- Full-scale rolling-origin backtests show pipeline realization adjustment wins WAPE at 4/8/12 weeks, but still underforecasts at 8 and 12 weeks. Results vary by seed and synthetic demand profile.
- Perfect detector scores on the three tested seeds reflect deterministic injected conditions matching deterministic rules. They should not be interpreted as production precision or recall.
- The stale-skill anomaly is an expired skill incorrectly marked `Current`; it does not model a separate stale proficiency value.
- A deliberate exception fixture leaves one Active allocation on a Cancelled project to demonstrate lifecycle exception handling. It is not a production cancellation policy.
- In the audited full run, 8,001 of 265,000 employee-weeks (3.019%) had zero availability. Leave covers 80.020% of employees, is modeled across all months with July and December peaks, and only six fixed holidays are included.
- Full-scale generation and validation took 87.16 seconds with a sampled peak process-tree working set of 739.9 MiB on the local Windows/Python 3.14.7 environment. Other platforms and machines were not benchmarked, and sub-250-ms memory peaks may be missed.
- NumPy `Generator` stream output is guaranteed only under the pinned NumPy version. Starter artifact hashes matched under Python 3.11.15 and 3.14.7; the manifest's runtime-version field itself is expected to differ.
- Hash evidence covers canonical CSV/JSON/SQL files and a logical SQLite dump, not raw SQLite file bytes.
- The test suite measured 92% overall coverage; CLI coverage was 55%, with a `CliRunner` smoke test for `generate`. The README command sequence was separately checked in a fresh clone.
- GNU Make and remote GitHub Actions were not run in the audited Windows environment because Make was unavailable. Direct `uv run` checks passed; no remote CI success is claimed.
- The public GitHub push requested by the problem statement was not performed or verified.
