# Assumptions

- The supplied specification is authoritative; unspecified categorical values are deterministic synthetic values.
- Starter scale is the default for local runs. Full scale uses the same generation functions and fixed 2026 calendar.
- Project and employee labels are generated identifiers only; no personal names or contact data are present.
- ISO weeks are Monday through Sunday. The as-of date is fixed at 2026-10-22 and does not depend on the machine clock.
- Sample output is generated locally from the pinned dependencies; forecast and evaluation metrics describe synthetic data only.
- An allocation percentage is a fraction of that employee-week's available hours, not nominal 40-hour capacity.
- Business-key duplicates among Approved demand lines are data-quality findings rather than SQLite constraints so the injected case can be loaded and evaluated.
- The starter and full sizes are configuration-driven. Test fixtures can use smaller counts while calling the same generation functions.
- The anomaly-rate setting applies to each eligible anomaly target population independently; at least one example from every specified family is retained.
- Baseline skill expiry is deliberately distributed around the fixed AS_OF date to produce approximately 15% stale skills; wrong flags are injected only after that baseline is created.
