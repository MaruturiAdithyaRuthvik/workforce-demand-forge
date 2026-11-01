# Design decisions

- Demand uses a project-week `DemandPlan` header identifier and separate role/skill `DemandLine` records. Thus each project-week can contain multiple role/skill requirements while retaining the specified `DEM-<project>-<week>` identifier.
- Source tables are generated before derived availability, utilization, supply, gap, and action records. Anomaly injection modifies source fields before derived tables are recalculated.
- Seed streams use a deterministic NumPy `SeedSequence` spawn key per entity family. Independent entity generation is isolated from changes to other families.
- The database enforces primary keys, foreign keys, and row-level checks. Business-key uniqueness for approved demand is checked in Python so anomaly fixtures can be loaded.
- The configured 2% anomaly rate is applied independently to each eligible target population, with at least one example for each required anomaly family. Ground truth keys are source record IDs so evaluation can match detections without detector access to labels.
- Pipeline confidence is configured in `config/default.yaml`: Planned 0.45, Active 0.8, Completed 0.0, and Cancelled 0.0. Historical backtests recompute project lifecycle as of each origin date and exclude plan lines created after that origin.
