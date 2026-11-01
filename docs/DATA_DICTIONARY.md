# Data dictionary

Generated from the Pydantic table models in `wdf/models.py`; rerun `python scripts/update_data_dictionary.py` after schema changes.

## `roles`

| Field | Type | Required | Allowed values | Units | Uniqueness | Validation |
|---|---|---|---|---|---|---|
| role_id | string | yes | — | none | primary key | ROLE-0001 four-digit identifier. |
| title | string | yes | — | none | not unique | non-empty synthetic job title. |
| family | string | yes | Engineering, Data, QA, Design, PM, DevOps, Security, Support | none | not unique | one of the listed role families. |

## `skills`

| Field | Type | Required | Allowed values | Units | Uniqueness | Validation |
|---|---|---|---|---|---|---|
| skill_id | string | yes | — | none | primary key | SKL-000001 six-digit identifier. |
| name | string | yes | — | none | not unique | synthetic skill label. |
| category | string | yes | Technical, Domain, Leadership, Platform, Compliance | none | not unique | one of the listed categories. |
| validity_months | integer | yes | — | months | not unique | positive integer. |

## `proficiency_scale`

| Field | Type | Required | Allowed values | Units | Uniqueness | Validation |
|---|---|---|---|---|---|---|
| proficiency | integer | yes | — | ordinal level | primary key | integer 1 through 5. |
| definition | string | yes | — | none | not unique | non-empty level definition. |

## `role_skills`

| Field | Type | Required | Allowed values | Units | Uniqueness | Validation |
|---|---|---|---|---|---|---|
| role_skill_id | string | yes | — | none | primary key | stable bridge identifier. |
| role_id | string | yes | — | none | foreign key | references Role. |
| skill_id | string | yes | — | none | foreign key | references Skill. |
| min_proficiency | integer | yes | — | ordinal level | not unique | integer 1 through 5. |
| importance | number | yes | — | proportion | not unique | between zero and one. |

## `employees`

| Field | Type | Required | Allowed values | Units | Uniqueness | Validation |
|---|---|---|---|---|---|---|
| employee_id | string | yes | — | none | primary key | EMP-000001 six-digit identifier. |
| role_id | string | yes | — | none | foreign key | references Role. |
| manager_id | string \| null | no | — | none | optional foreign key | self-reference to Employee or null. |
| employment_type | string | yes | FT, PT | none | not unique | FT or PT. |
| fte | number | yes | 1.0, 0.8, 0.6, 0.5 | FTE | not unique | one of 1.0, 0.8, 0.6, 0.5. |
| hire_date | string | yes | — | ISO date | not unique | valid ISO-8601 date. |
| status | string | yes | Active, Inactive | none | not unique | legal employee lifecycle state. |

## `employee_skills`

| Field | Type | Required | Allowed values | Units | Uniqueness | Validation |
|---|---|---|---|---|---|---|
| employee_skill_id | string | yes | — | none | primary key | ESK-000001 six-digit identifier. |
| employee_id | string | yes | — | none | foreign key | references Employee. |
| skill_id | string | yes | — | none | foreign key | references Skill. |
| proficiency | integer | yes | — | ordinal level | not unique | integer 1 through 5. |
| last_verified_date | string | yes | — | ISO date | not unique | not after expiry_date. |
| expiry_date | string | yes | — | ISO date | not unique | last_verified_date plus skill validity. |
| currency_flag | string | yes | Current, Stale | none | not unique | source-system skill currency flag. |

## `projects`

| Field | Type | Required | Allowed values | Units | Uniqueness | Validation |
|---|---|---|---|---|---|---|
| project_id | string | yes | — | none | primary key | PRJ-2026-000001 identifier. |
| start_date | string | yes | — | ISO date | not unique | on or before end_date. |
| end_date | string | yes | — | ISO date | not unique | on or after start_date. |
| priority | string | yes | Low, Medium, High, Critical | none | not unique | listed priority enum. |
| staffing_model | string | yes | Shared-Pool, Dedicated-Team | none | not unique | listed staffing model. |
| demand_profile | string | yes | ramp_up, steady, ramp_down | none | not unique | configured project demand curve. |
| status | string | yes | Planned, Active, Completed, Cancelled | none | not unique | legal project lifecycle state. |

## `demand_plans`

| Field | Type | Required | Allowed values | Units | Uniqueness | Validation |
|---|---|---|---|---|---|---|
| demand_id | string | yes | — | none | primary key | DEM-<project>-2026Wnn. |
| project_id | string | yes | — | none | foreign key | references Project. |
| iso_week | string | yes | — | ISO week | not unique | 2026W01 through 2026W53. |
| week_start | string | yes | — | ISO date | not unique | Monday for iso_week. |

## `demand_lines`

| Field | Type | Required | Allowed values | Units | Uniqueness | Validation |
|---|---|---|---|---|---|---|
| demand_line_id | string | yes | — | none | primary key | DEML-000001 six-digit identifier. |
| demand_id | string | yes | — | none | foreign key | references DemandPlan. |
| project_id | string | yes | — | none | foreign key | references Project. |
| iso_week | string | yes | — | ISO week | not unique | 2026 ISO week. |
| role_id | string | yes | — | none | foreign key | references Role. |
| skill_id | string | yes | — | none | foreign key | references Skill. |
| required_fte | number | yes | — | FTE | not unique | positive demand. |
| min_proficiency | integer | yes | — | ordinal level | not unique | integer 1 through 5. |
| source | string | yes | PlanTool, ResourceRequest | none | not unique | listed source enum. |
| created_on | string | yes | — | ISO date | not unique | valid creation date. |
| supersedes_line_id | string \| null | no | — | none | optional foreign key | references DemandLine. |
| status | string | yes | Draft, Approved, Superseded | none | not unique | legal demand lifecycle state. |

## `leave`

| Field | Type | Required | Allowed values | Units | Uniqueness | Validation |
|---|---|---|---|---|---|---|
| leave_id | string | yes | — | none | primary key | LEAVE-000001 identifier. |
| employee_id | string | yes | — | none | foreign key | references Employee. |
| start_date | string | yes | — | ISO date | not unique | on or before end_date. |
| end_date | string | yes | — | ISO date | not unique | on or after start_date. |
| leave_type | string | yes | Annual, Sick, Care, Other | none | not unique | listed leave type. |
| status | string | yes | Approved, Pending, Rejected | none | not unique | listed leave state. |

## `holidays`

| Field | Type | Required | Allowed values | Units | Uniqueness | Validation |
|---|---|---|---|---|---|---|
| holiday_date | string | yes | — | ISO date | primary key | fixed synthetic holiday date. |
| name | string | yes | — | none | not unique | synthetic label. |

## `allocations`

| Field | Type | Required | Allowed values | Units | Uniqueness | Validation |
|---|---|---|---|---|---|---|
| allocation_id | string | yes | — | none | primary key | ALLOC-2026-000001 six-digit identifier. |
| employee_id | string | yes | — | none | foreign key | references Employee. |
| project_id | string | yes | — | none | foreign key | references Project. |
| role_id | string | yes | — | none | foreign key | references Role. |
| start_date | string | yes | — | ISO date | not unique | on or before end_date. |
| end_date | string | yes | — | ISO date | not unique | on or after start_date. |
| allocation_pct | number | yes | — | proportion of weekly available hours | not unique | positive. |
| skill_basis_esk_id | string \| null | no | — | none | optional foreign key | references EmployeeSkill. |
| status | string | yes | Proposed, Active, Completed, Cancelled | none | not unique | legal allocation lifecycle state. |

## `training`

| Field | Type | Required | Allowed values | Units | Uniqueness | Validation |
|---|---|---|---|---|---|---|
| training_id | string | yes | — | none | primary key | TRN-000001 six-digit identifier. |
| employee_id | string | yes | — | none | foreign key | references Employee. |
| skill_id | string | yes | — | none | foreign key | references Skill. |
| target_proficiency | integer | yes | — | ordinal level | not unique | integer 1 through 5. |
| cost | number | yes | — | synthetic currency units | not unique | non-negative. |
| start_date | string | yes | — | ISO date | not unique | on or before end_date. |
| end_date | string | yes | — | ISO date | not unique | on or after start_date. |
| status | string | yes | Planned, Enrolled, Completed, Failed, Cancelled | none | not unique | legal training lifecycle state. |

## `lifecycle_events`

| Field | Type | Required | Allowed values | Units | Uniqueness | Validation |
|---|---|---|---|---|---|---|
| event_id | string | yes | — | none | primary key | EVT-000001 six-digit identifier. |
| entity_type | string | yes | Employee, Project, Allocation, Training, DemandLine | none | not unique | listed event entity. |
| entity_id | string | yes | — | none | polymorphic reference | references entity_id for entity_type. |
| from_state | string \| null | no | — | none | not unique | previous lifecycle state or null for first event. |
| to_state | string | yes | — | none | not unique | legal transition target. |
| effective_date | string | yes | — | ISO date | not unique | valid effective date. |
| reason | string | yes | — | none | not unique | non-empty synthetic reason. |

## `availability`

| Field | Type | Required | Allowed values | Units | Uniqueness | Validation |
|---|---|---|---|---|---|---|
| availability_id | string | yes | — | none | primary key | AVL-000001 six-digit identifier. |
| employee_id | string | yes | — | none | foreign key | references Employee. |
| iso_week | string | yes | — | ISO week | employee and week | 2026 ISO week. |
| capacity_hours | number | yes | — | hours per week | not unique | 40 times employee FTE. |
| leave_hours | number | yes | — | hours per week | not unique | derived from approved leave. |
| holiday_hours | number | yes | — | hours per week | not unique | derived from fixed holidays. |
| available_hours | number | yes | — | hours per week | not unique | capacity minus leave and holiday hours. |

## `utilization`

| Field | Type | Required | Allowed values | Units | Uniqueness | Validation |
|---|---|---|---|---|---|---|
| utilization_id | string | yes | — | none | primary key | UTL employee-week identifier. |
| employee_id | string | yes | — | none | foreign key | references Employee. |
| iso_week | string | yes | — | ISO week | employee and week | 2026 ISO week. |
| allocation_pct_sum | number | yes | — | proportion | not unique | sum of applicable allocation percentages. |
| allocated_hours | number | yes | — | hours per week | not unique | pct sum times available hours. |
| utilization_available | number \| null | no | — | proportion | not unique | null when available hours is zero. |
| utilization_capacity | number \| null | no | — | proportion | not unique | allocated hours divided by capacity. |
| flag | string \| null | no | — | none | not unique | ZERO_AVAILABILITY or null. |

## `supply`

| Field | Type | Required | Allowed values | Units | Uniqueness | Validation |
|---|---|---|---|---|---|---|
| iso_week | string | yes | — | ISO week | role and skill and week | 2026 ISO week. |
| role_id | string | yes | — | none | foreign key | references Role. |
| skill_id | string | yes | — | none | foreign key | references Skill. |
| supply_fte | number | yes | — | FTE | not unique | sum of eligible available hours divided by 40. |
| supporting_esk_ids | array<string> | yes | — | none | not unique | EmployeeSkill IDs supporting supply. |

## `gap_analysis`

| Field | Type | Required | Allowed values | Units | Uniqueness | Validation |
|---|---|---|---|---|---|---|
| gap_id | string | yes | — | none | primary key | GAP-2026Wnn-000001. |
| iso_week | string | yes | — | ISO week | role and skill and week | 2026 ISO week. |
| role_id | string | yes | — | none | foreign key | references Role. |
| skill_id | string | yes | — | none | foreign key | references Skill. |
| demand_fte | number | yes | — | FTE | not unique | sum of Approved demand lines. |
| supply_fte | number | yes | — | FTE | not unique | derived eligible supply. |
| gap_fte | number | yes | — | FTE | not unique | demand_fte minus supply_fte. |
| risk_level | string | yes | Covered, Low, Medium, High | none | not unique | config threshold classification. |
| source_demand_line_ids | array<string> | yes | — | none | not unique | Approved demand line IDs. |
| supporting_esk_ids | array<string> | yes | — | none | not unique | eligible EmployeeSkill IDs. |

## `gap_actions`

| Field | Type | Required | Allowed values | Units | Uniqueness | Validation |
|---|---|---|---|---|---|---|
| gap_action_id | string | yes | — | none | primary key | GACT-000001 six-digit identifier. |
| gap_id | string \| null | no | — | none | optional foreign key | references GapAnalysis or null for utilization actions. |
| action_type | string | yes | Reverify, Train, Hire, Reallocate, Contract | none | not unique | listed action. |
| candidate_employee_id | string \| null | no | — | none | optional foreign key | references Employee. |
| candidate_skill_id | string \| null | no | — | none | optional foreign key | references Skill. |
| source_utilization_id | string \| null | no | — | none | optional foreign key | references Utilization. |
| source_allocation_ids | array<string> | no | — | none | not unique | source Allocation IDs. |
| rule_id | string | yes | — | none | not unique | non-empty rule identifier. |
| owner_actor | string | yes | Employee, Manager, HR Partner, IT/Ops Partner, System Admin | none | not unique | listed accountable actor. |
| status | string | yes | Proposed, Approved, InProgress, Done, Rejected, Escalated | none | not unique | listed action lifecycle. |
| lead_time_weeks | integer | yes | — | weeks | not unique | non-negative. |
| estimated_cost | number | yes | — | synthetic currency units | not unique | non-negative. |
| assumptions | string | yes | — | none | not unique | documents rule and thresholds. |
