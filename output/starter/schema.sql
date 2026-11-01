PRAGMA foreign_keys = ON;

CREATE TABLE "allocations" (
  "allocation_id" TEXT,
  "employee_id" TEXT,
  "project_id" TEXT,
  "role_id" TEXT,
  "start_date" TEXT,
  "end_date" TEXT,
  "allocation_pct" REAL,
  "skill_basis_esk_id" TEXT,
  "status" TEXT,
  PRIMARY KEY ("allocation_id"),
  FOREIGN KEY ("employee_id") REFERENCES "employees"("employee_id"),
  FOREIGN KEY ("project_id") REFERENCES "projects"("project_id"),
  FOREIGN KEY ("role_id") REFERENCES "roles"("role_id"),
  FOREIGN KEY ("skill_basis_esk_id") REFERENCES "employee_skills"("employee_skill_id"),
  CHECK ("status" IN ('Proposed', 'Active', 'Completed', 'Cancelled'))
);

CREATE TABLE "availability" (
  "availability_id" TEXT,
  "employee_id" TEXT,
  "iso_week" TEXT,
  "capacity_hours" REAL,
  "leave_hours" REAL,
  "holiday_hours" REAL,
  "available_hours" REAL,
  PRIMARY KEY ("availability_id"),
  FOREIGN KEY ("employee_id") REFERENCES "employees"("employee_id")
);

CREATE TABLE "demand_lines" (
  "demand_line_id" TEXT,
  "demand_id" TEXT,
  "project_id" TEXT,
  "iso_week" TEXT,
  "role_id" TEXT,
  "skill_id" TEXT,
  "required_fte" REAL,
  "min_proficiency" INTEGER,
  "source" TEXT,
  "created_on" TEXT,
  "supersedes_line_id" TEXT,
  "status" TEXT,
  PRIMARY KEY ("demand_line_id"),
  FOREIGN KEY ("demand_id") REFERENCES "demand_plans"("demand_id"),
  FOREIGN KEY ("project_id") REFERENCES "projects"("project_id"),
  FOREIGN KEY ("role_id") REFERENCES "roles"("role_id"),
  FOREIGN KEY ("skill_id") REFERENCES "skills"("skill_id"),
  FOREIGN KEY ("supersedes_line_id") REFERENCES "demand_lines"("demand_line_id"),
  CHECK ("source" IN ('PlanTool', 'ResourceRequest')),
  CHECK ("status" IN ('Draft', 'Approved', 'Superseded'))
);

CREATE TABLE "demand_plans" (
  "demand_id" TEXT,
  "project_id" TEXT,
  "iso_week" TEXT,
  "week_start" TEXT,
  PRIMARY KEY ("demand_id"),
  FOREIGN KEY ("project_id") REFERENCES "projects"("project_id")
);

CREATE TABLE "employee_skills" (
  "employee_skill_id" TEXT,
  "employee_id" TEXT,
  "skill_id" TEXT,
  "proficiency" INTEGER,
  "last_verified_date" TEXT,
  "expiry_date" TEXT,
  "currency_flag" TEXT,
  PRIMARY KEY ("employee_skill_id"),
  FOREIGN KEY ("employee_id") REFERENCES "employees"("employee_id"),
  FOREIGN KEY ("skill_id") REFERENCES "skills"("skill_id"),
  CHECK ("currency_flag" IN ('Current', 'Stale'))
);

CREATE TABLE "employees" (
  "employee_id" TEXT,
  "role_id" TEXT,
  "manager_id" TEXT,
  "employment_type" TEXT,
  "fte" REAL,
  "hire_date" TEXT,
  "status" TEXT,
  PRIMARY KEY ("employee_id"),
  FOREIGN KEY ("role_id") REFERENCES "roles"("role_id"),
  FOREIGN KEY ("manager_id") REFERENCES "employees"("employee_id"),
  CHECK ("employment_type" IN ('FT', 'PT')),
  CHECK ("status" IN ('Active', 'Inactive')),
  CHECK ("fte" IN (1.0, 0.8, 0.6, 0.5))
);

CREATE TABLE "gap_actions" (
  "gap_action_id" TEXT,
  "gap_id" TEXT,
  "action_type" TEXT,
  "candidate_employee_id" TEXT,
  "candidate_skill_id" TEXT,
  "rule_id" TEXT,
  "owner_actor" TEXT,
  "status" TEXT,
  "lead_time_weeks" INTEGER,
  "estimated_cost" REAL,
  "assumptions" TEXT,
  PRIMARY KEY ("gap_action_id"),
  FOREIGN KEY ("gap_id") REFERENCES "gap_analysis"("gap_id"),
  FOREIGN KEY ("candidate_employee_id") REFERENCES "employees"("employee_id"),
  FOREIGN KEY ("candidate_skill_id") REFERENCES "skills"("skill_id"),
  CHECK ("action_type" IN ('Reverify', 'Train', 'Hire', 'Reallocate', 'Contract')),
  CHECK ("owner_actor" IN ('Employee', 'Manager', 'HR Partner', 'IT/Ops Partner', 'System Admin')),
  CHECK ("status" IN ('Proposed', 'Approved', 'InProgress', 'Done', 'Rejected', 'Escalated'))
);

CREATE TABLE "gap_analysis" (
  "gap_id" TEXT,
  "iso_week" TEXT,
  "role_id" TEXT,
  "skill_id" TEXT,
  "demand_fte" REAL,
  "supply_fte" REAL,
  "gap_fte" REAL,
  "risk_level" TEXT,
  "source_demand_line_ids" TEXT,
  "supporting_esk_ids" TEXT,
  PRIMARY KEY ("gap_id"),
  FOREIGN KEY ("role_id") REFERENCES "roles"("role_id"),
  FOREIGN KEY ("skill_id") REFERENCES "skills"("skill_id"),
  CHECK ("risk_level" IN ('Covered', 'Low', 'Medium', 'High'))
);

CREATE TABLE "holidays" (
  "holiday_date" TEXT,
  "name" TEXT,
  PRIMARY KEY ("holiday_date")
);

CREATE TABLE "leave" (
  "leave_id" TEXT,
  "employee_id" TEXT,
  "start_date" TEXT,
  "end_date" TEXT,
  "leave_type" TEXT,
  "status" TEXT,
  PRIMARY KEY ("leave_id"),
  FOREIGN KEY ("employee_id") REFERENCES "employees"("employee_id"),
  CHECK ("leave_type" IN ('Annual', 'Sick', 'Care', 'Other')),
  CHECK ("status" IN ('Approved', 'Pending', 'Rejected'))
);

CREATE TABLE "lifecycle_events" (
  "event_id" TEXT,
  "entity_type" TEXT,
  "entity_id" TEXT,
  "from_state" TEXT,
  "to_state" TEXT,
  "effective_date" TEXT,
  "reason" TEXT,
  PRIMARY KEY ("event_id"),
  CHECK ("entity_type" IN ('Employee', 'Project', 'Allocation', 'Training', 'DemandLine'))
);

CREATE TABLE "proficiency_scale" (
  "proficiency" INTEGER,
  "definition" TEXT,
  PRIMARY KEY ("proficiency")
);

CREATE TABLE "projects" (
  "project_id" TEXT,
  "start_date" TEXT,
  "end_date" TEXT,
  "priority" TEXT,
  "staffing_model" TEXT,
  "status" TEXT,
  PRIMARY KEY ("project_id"),
  CHECK ("priority" IN ('Low', 'Medium', 'High', 'Critical')),
  CHECK ("staffing_model" IN ('Shared-Pool', 'Dedicated-Team')),
  CHECK ("status" IN ('Planned', 'Active', 'Completed', 'Cancelled'))
);

CREATE TABLE "role_skills" (
  "role_skill_id" TEXT,
  "role_id" TEXT,
  "skill_id" TEXT,
  "min_proficiency" INTEGER,
  "importance" REAL,
  PRIMARY KEY ("role_skill_id"),
  FOREIGN KEY ("role_id") REFERENCES "roles"("role_id"),
  FOREIGN KEY ("skill_id") REFERENCES "skills"("skill_id")
);

CREATE TABLE "roles" (
  "role_id" TEXT,
  "title" TEXT,
  "family" TEXT,
  PRIMARY KEY ("role_id"),
  CHECK ("family" IN ('Engineering', 'Data', 'QA', 'Design', 'PM', 'DevOps', 'Security', 'Support'))
);

CREATE TABLE "skills" (
  "skill_id" TEXT,
  "name" TEXT,
  "category" TEXT,
  "validity_months" INTEGER,
  PRIMARY KEY ("skill_id"),
  CHECK ("category" IN ('Technical', 'Domain', 'Leadership', 'Platform', 'Compliance'))
);

CREATE TABLE "supply" (
  "iso_week" TEXT,
  "role_id" TEXT,
  "skill_id" TEXT,
  "supply_fte" REAL,
  "supporting_esk_ids" TEXT,
  PRIMARY KEY ("iso_week", "role_id", "skill_id"),
  FOREIGN KEY ("role_id") REFERENCES "roles"("role_id"),
  FOREIGN KEY ("skill_id") REFERENCES "skills"("skill_id")
);

CREATE TABLE "training" (
  "training_id" TEXT,
  "employee_id" TEXT,
  "skill_id" TEXT,
  "target_proficiency" INTEGER,
  "cost" REAL,
  "start_date" TEXT,
  "end_date" TEXT,
  "status" TEXT,
  PRIMARY KEY ("training_id"),
  FOREIGN KEY ("employee_id") REFERENCES "employees"("employee_id"),
  FOREIGN KEY ("skill_id") REFERENCES "skills"("skill_id"),
  CHECK ("status" IN ('Planned', 'Enrolled', 'Completed', 'Failed', 'Cancelled'))
);

CREATE TABLE "utilization" (
  "utilization_id" TEXT,
  "employee_id" TEXT,
  "iso_week" TEXT,
  "allocation_pct_sum" REAL,
  "allocated_hours" REAL,
  "utilization_available" REAL,
  "utilization_capacity" REAL,
  "flag" TEXT,
  PRIMARY KEY ("utilization_id"),
  FOREIGN KEY ("employee_id") REFERENCES "employees"("employee_id")
);
