# Design decisions

- Demand uses a project-week `DemandPlan` header identifier and separate role/skill `DemandLine` records. Thus each project-week can contain multiple role/skill requirements while retaining the specified `DEM-<project>-<week>` identifier.
- Source tables are generated before derived availability, utilization, supply, gap, and action records. Anomaly injection modifies source fields before derived tables are recalculated.
- Seed streams use a deterministic NumPy `SeedSequence` spawn key per entity family. Independent entity generation is isolated from changes to other families.
- The database enforces primary keys, foreign keys, and row-level checks. Business-key uniqueness for approved demand is checked in Python so anomaly fixtures can be loaded.
