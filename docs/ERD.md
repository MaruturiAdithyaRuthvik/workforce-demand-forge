# Entity relationship diagram

```mermaid
erDiagram
  Role ||--o{ Employee : assigns
  Role ||--o{ RoleSkill : requires
  Skill ||--o{ RoleSkill : qualifies
  Employee ||--o{ EmployeeSkill : holds
  Skill ||--o{ EmployeeSkill : verified_as
  Project ||--o{ DemandPlan : plans
  DemandPlan ||--o{ DemandLine : contains
  Role ||--o{ DemandLine : requests
  Skill ||--o{ DemandLine : requests
  Employee ||--o{ Leave : takes
  Employee ||--o{ Availability : has
  Employee ||--o{ Allocation : receives
  Project ||--o{ Allocation : staffs
  EmployeeSkill o|--o{ Allocation : may_justify
  Employee ||--o{ Training : attends
  Skill ||--o{ Training : targets
  Role ||--o{ Supply : qualifies
  Skill ||--o{ Supply : qualifies
  Role ||--o{ GapAnalysis : measures
  Skill ||--o{ GapAnalysis : measures
  GapAnalysis o|--o{ GapAction : recommends
  Employee o|--o{ GapAction : candidate
  Skill o|--o{ GapAction : candidate
```

`RoleSkill` and `EmployeeSkill` are bridge entities for the Role↔Skill and Employee↔Skill many-to-many relationships. Project-week headers have one `DemandPlan` per project and ISO week; each header has one or more role/skill `DemandLine` children. A demand line's `supersedes_line_id` is an optional self-reference; revisions are append-only.

Every `Availability` and `Utilization` row is effective for one employee-week. Allocation, leave, project, training, and lifecycle records carry effective dates. `LifecycleEvent` is append-only and polymorphically references Employee, Project, Allocation, Training, or DemandLine; current state is the final event in effective-date order. SQL cannot express that polymorphic relation as a single foreign key, so the validator checks its referential and state consistency.

Forecasts are derived CSV outputs rather than SQLite entities: `forecast.csv` is keyed by role/week/method, and `forecast_project.csv` adds Project to that key. Project-level rows are allocated using only historical or origin-visible project demand; their FTE totals reconcile to the corresponding role-level forecast. `metrics.json` reports rolling-origin scores at both levels.

```mermaid
stateDiagram-v2
  [*] --> Planned
  Planned --> Active
  Planned --> Cancelled
  Active --> Completed
  Active --> Cancelled
```

The project lifecycle is shown above. Allocation transitions are Proposed→Active→Completed|Cancelled. Training transitions are Planned→Enrolled→Completed|Failed|Cancelled. DemandLine transitions are Draft→Approved→Superseded. Each entity's transition history is validated against its current-state column.
