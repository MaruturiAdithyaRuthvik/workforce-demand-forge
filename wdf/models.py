from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Row(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Role(Row):
    role_id: str = Field(description="units=none; uniqueness=primary key; validation=ROLE-0001 four-digit identifier.")
    title: str = Field(description="units=none; uniqueness=not unique; validation=non-empty synthetic job title.")
    family: Literal["Engineering", "Data", "QA", "Design", "PM", "DevOps", "Security", "Support"] = Field(
        description="units=none; uniqueness=not unique; validation=one of the listed role families."
    )


class Skill(Row):
    skill_id: str = Field(description="units=none; uniqueness=primary key; validation=SKL-000001 six-digit identifier.")
    name: str = Field(description="units=none; uniqueness=not unique; validation=synthetic skill label.")
    category: Literal["Technical", "Domain", "Leadership", "Platform", "Compliance"] = Field(
        description="units=none; uniqueness=not unique; validation=one of the listed categories."
    )
    validity_months: int = Field(ge=1, description="units=months; uniqueness=not unique; validation=positive integer.")


class ProficiencyScale(Row):
    proficiency: int = Field(ge=1, le=5, description="units=ordinal level; uniqueness=primary key; validation=integer 1 through 5.")
    definition: str = Field(description="units=none; uniqueness=not unique; validation=non-empty level definition.")


class RoleSkill(Row):
    role_skill_id: str = Field(description="units=none; uniqueness=primary key; validation=stable bridge identifier.")
    role_id: str = Field(description="units=none; uniqueness=foreign key; validation=references Role.")
    skill_id: str = Field(description="units=none; uniqueness=foreign key; validation=references Skill.")
    min_proficiency: int = Field(ge=1, le=5, description="units=ordinal level; uniqueness=not unique; validation=integer 1 through 5.")
    importance: float = Field(ge=0, le=1, description="units=proportion; uniqueness=not unique; validation=between zero and one.")


class Employee(Row):
    employee_id: str = Field(description="units=none; uniqueness=primary key; validation=EMP-000001 six-digit identifier.")
    role_id: str = Field(description="units=none; uniqueness=foreign key; validation=references Role.")
    manager_id: str | None = Field(default=None, description="units=none; uniqueness=optional foreign key; validation=self-reference to Employee or null.")
    employment_type: Literal["FT", "PT"] = Field(description="units=none; uniqueness=not unique; validation=FT or PT.")
    fte: Literal[1.0, 0.8, 0.6, 0.5] = Field(description="units=FTE; uniqueness=not unique; validation=one of 1.0, 0.8, 0.6, 0.5.")
    hire_date: str = Field(description="units=ISO date; uniqueness=not unique; validation=valid ISO-8601 date.")
    status: Literal["Active", "Inactive"] = Field(description="units=none; uniqueness=not unique; validation=legal employee lifecycle state.")


class EmployeeSkill(Row):
    employee_skill_id: str = Field(description="units=none; uniqueness=primary key; validation=ESK-000001 six-digit identifier.")
    employee_id: str = Field(description="units=none; uniqueness=foreign key; validation=references Employee.")
    skill_id: str = Field(description="units=none; uniqueness=foreign key; validation=references Skill.")
    proficiency: int = Field(ge=1, le=5, description="units=ordinal level; uniqueness=not unique; validation=integer 1 through 5.")
    last_verified_date: str = Field(description="units=ISO date; uniqueness=not unique; validation=not after expiry_date.")
    expiry_date: str = Field(description="units=ISO date; uniqueness=not unique; validation=last_verified_date plus skill validity.")
    currency_flag: Literal["Current", "Stale"] = Field(description="units=none; uniqueness=not unique; validation=source-system skill currency flag.")


class Project(Row):
    project_id: str = Field(description="units=none; uniqueness=primary key; validation=PRJ-2026-000001 identifier.")
    start_date: str = Field(description="units=ISO date; uniqueness=not unique; validation=on or before end_date.")
    end_date: str = Field(description="units=ISO date; uniqueness=not unique; validation=on or after start_date.")
    priority: Literal["Low", "Medium", "High", "Critical"] = Field(description="units=none; uniqueness=not unique; validation=listed priority enum.")
    staffing_model: Literal["Shared-Pool", "Dedicated-Team"] = Field(description="units=none; uniqueness=not unique; validation=listed staffing model.")
    demand_profile: Literal["ramp_up", "steady", "ramp_down"] = Field(description="units=none; uniqueness=not unique; validation=configured project demand curve.")
    status: Literal["Planned", "Active", "Completed", "Cancelled"] = Field(description="units=none; uniqueness=not unique; validation=legal project lifecycle state.")


class DemandPlan(Row):
    demand_id: str = Field(description="units=none; uniqueness=primary key; validation=DEM-<project>-2026Wnn.")
    project_id: str = Field(description="units=none; uniqueness=foreign key; validation=references Project.")
    iso_week: str = Field(description="units=ISO week; uniqueness=not unique; validation=2026W01 through 2026W53.")
    week_start: str = Field(description="units=ISO date; uniqueness=not unique; validation=Monday for iso_week.")


class DemandLine(Row):
    demand_line_id: str = Field(description="units=none; uniqueness=primary key; validation=DEML-000001 six-digit identifier.")
    demand_id: str = Field(description="units=none; uniqueness=foreign key; validation=references DemandPlan.")
    project_id: str = Field(description="units=none; uniqueness=foreign key; validation=references Project.")
    iso_week: str = Field(description="units=ISO week; uniqueness=not unique; validation=2026 ISO week.")
    role_id: str = Field(description="units=none; uniqueness=foreign key; validation=references Role.")
    skill_id: str = Field(description="units=none; uniqueness=foreign key; validation=references Skill.")
    required_fte: float = Field(gt=0, description="units=FTE; uniqueness=not unique; validation=positive demand.")
    min_proficiency: int = Field(ge=1, le=5, description="units=ordinal level; uniqueness=not unique; validation=integer 1 through 5.")
    source: Literal["PlanTool", "ResourceRequest"] = Field(description="units=none; uniqueness=not unique; validation=listed source enum.")
    created_on: str = Field(description="units=ISO date; uniqueness=not unique; validation=valid creation date.")
    supersedes_line_id: str | None = Field(default=None, description="units=none; uniqueness=optional foreign key; validation=references DemandLine.")
    status: Literal["Draft", "Approved", "Superseded"] = Field(description="units=none; uniqueness=not unique; validation=legal demand lifecycle state.")


class Leave(Row):
    leave_id: str = Field(description="units=none; uniqueness=primary key; validation=LEAVE-000001 identifier.")
    employee_id: str = Field(description="units=none; uniqueness=foreign key; validation=references Employee.")
    start_date: str = Field(description="units=ISO date; uniqueness=not unique; validation=on or before end_date.")
    end_date: str = Field(description="units=ISO date; uniqueness=not unique; validation=on or after start_date.")
    leave_type: Literal["Annual", "Sick", "Care", "Other"] = Field(description="units=none; uniqueness=not unique; validation=listed leave type.")
    status: Literal["Approved", "Pending", "Rejected"] = Field(description="units=none; uniqueness=not unique; validation=listed leave state.")


class Holiday(Row):
    holiday_date: str = Field(description="units=ISO date; uniqueness=primary key; validation=fixed synthetic holiday date.")
    name: str = Field(description="units=none; uniqueness=not unique; validation=synthetic label.")


class Allocation(Row):
    allocation_id: str = Field(description="units=none; uniqueness=primary key; validation=ALLOC-2026-000001 six-digit identifier.")
    employee_id: str = Field(description="units=none; uniqueness=foreign key; validation=references Employee.")
    project_id: str = Field(description="units=none; uniqueness=foreign key; validation=references Project.")
    role_id: str = Field(description="units=none; uniqueness=foreign key; validation=references Role.")
    start_date: str = Field(description="units=ISO date; uniqueness=not unique; validation=on or before end_date.")
    end_date: str = Field(description="units=ISO date; uniqueness=not unique; validation=on or after start_date.")
    allocation_pct: float = Field(gt=0, description="units=proportion of weekly available hours; uniqueness=not unique; validation=positive.")
    skill_basis_esk_id: str | None = Field(default=None, description="units=none; uniqueness=optional foreign key; validation=references EmployeeSkill.")
    status: Literal["Proposed", "Active", "Completed", "Cancelled"] = Field(description="units=none; uniqueness=not unique; validation=legal allocation lifecycle state.")


class Training(Row):
    training_id: str = Field(description="units=none; uniqueness=primary key; validation=TRN-000001 six-digit identifier.")
    employee_id: str = Field(description="units=none; uniqueness=foreign key; validation=references Employee.")
    skill_id: str = Field(description="units=none; uniqueness=foreign key; validation=references Skill.")
    target_proficiency: int = Field(ge=1, le=5, description="units=ordinal level; uniqueness=not unique; validation=integer 1 through 5.")
    cost: float = Field(ge=0, description="units=synthetic currency units; uniqueness=not unique; validation=non-negative.")
    start_date: str = Field(description="units=ISO date; uniqueness=not unique; validation=on or before end_date.")
    end_date: str = Field(description="units=ISO date; uniqueness=not unique; validation=on or after start_date.")
    status: Literal["Planned", "Enrolled", "Completed", "Failed", "Cancelled"] = Field(description="units=none; uniqueness=not unique; validation=legal training lifecycle state.")


class LifecycleEvent(Row):
    event_id: str = Field(description="units=none; uniqueness=primary key; validation=EVT-000001 six-digit identifier.")
    entity_type: Literal["Employee", "Project", "Allocation", "Training", "DemandLine"] = Field(description="units=none; uniqueness=not unique; validation=listed event entity.")
    entity_id: str = Field(description="units=none; uniqueness=polymorphic reference; validation=references entity_id for entity_type.")
    from_state: str | None = Field(default=None, description="units=none; uniqueness=not unique; validation=previous lifecycle state or null for first event.")
    to_state: str = Field(description="units=none; uniqueness=not unique; validation=legal transition target.")
    effective_date: str = Field(description="units=ISO date; uniqueness=not unique; validation=valid effective date.")
    reason: str = Field(description="units=none; uniqueness=not unique; validation=non-empty synthetic reason.")


class Availability(Row):
    availability_id: str = Field(description="units=none; uniqueness=primary key; validation=AVL-000001 six-digit identifier.")
    employee_id: str = Field(description="units=none; uniqueness=foreign key; validation=references Employee.")
    iso_week: str = Field(description="units=ISO week; uniqueness=employee and week; validation=2026 ISO week.")
    capacity_hours: float = Field(ge=0, description="units=hours per week; uniqueness=not unique; validation=40 times employee FTE.")
    leave_hours: float = Field(ge=0, description="units=hours per week; uniqueness=not unique; validation=derived from approved leave.")
    holiday_hours: float = Field(ge=0, description="units=hours per week; uniqueness=not unique; validation=derived from fixed holidays.")
    available_hours: float = Field(ge=0, description="units=hours per week; uniqueness=not unique; validation=capacity minus leave and holiday hours.")


class Utilization(Row):
    utilization_id: str = Field(description="units=none; uniqueness=primary key; validation=UTL employee-week identifier.")
    employee_id: str = Field(description="units=none; uniqueness=foreign key; validation=references Employee.")
    iso_week: str = Field(description="units=ISO week; uniqueness=employee and week; validation=2026 ISO week.")
    allocation_pct_sum: float = Field(ge=0, description="units=proportion; uniqueness=not unique; validation=sum of applicable allocation percentages.")
    allocated_hours: float = Field(ge=0, description="units=hours per week; uniqueness=not unique; validation=pct sum times available hours.")
    utilization_available: float | None = Field(default=None, description="units=proportion; uniqueness=not unique; validation=null when available hours is zero.")
    utilization_capacity: float | None = Field(default=None, description="units=proportion; uniqueness=not unique; validation=allocated hours divided by capacity.")
    flag: str | None = Field(default=None, description="units=none; uniqueness=not unique; validation=ZERO_AVAILABILITY or null.")


class Supply(Row):
    iso_week: str = Field(description="units=ISO week; uniqueness=role and skill and week; validation=2026 ISO week.")
    role_id: str = Field(description="units=none; uniqueness=foreign key; validation=references Role.")
    skill_id: str = Field(description="units=none; uniqueness=foreign key; validation=references Skill.")
    supply_fte: float = Field(ge=0, description="units=FTE; uniqueness=not unique; validation=sum of eligible available hours divided by 40.")
    supporting_esk_ids: list[str] = Field(description="units=none; uniqueness=not unique; validation=EmployeeSkill IDs supporting supply.")


class GapAnalysis(Row):
    gap_id: str = Field(description="units=none; uniqueness=primary key; validation=GAP-2026Wnn-000001.")
    iso_week: str = Field(description="units=ISO week; uniqueness=role and skill and week; validation=2026 ISO week.")
    role_id: str = Field(description="units=none; uniqueness=foreign key; validation=references Role.")
    skill_id: str = Field(description="units=none; uniqueness=foreign key; validation=references Skill.")
    demand_fte: float = Field(ge=0, description="units=FTE; uniqueness=not unique; validation=sum of Approved demand lines.")
    supply_fte: float = Field(ge=0, description="units=FTE; uniqueness=not unique; validation=derived eligible supply.")
    gap_fte: float = Field(description="units=FTE; uniqueness=not unique; validation=demand_fte minus supply_fte.")
    risk_level: Literal["Covered", "Low", "Medium", "High"] = Field(description="units=none; uniqueness=not unique; validation=config threshold classification.")
    source_demand_line_ids: list[str] = Field(description="units=none; uniqueness=not unique; validation=Approved demand line IDs.")
    supporting_esk_ids: list[str] = Field(description="units=none; uniqueness=not unique; validation=eligible EmployeeSkill IDs.")


class GapAction(Row):
    gap_action_id: str = Field(description="units=none; uniqueness=primary key; validation=GACT-000001 six-digit identifier.")
    gap_id: str | None = Field(default=None, description="units=none; uniqueness=optional foreign key; validation=references GapAnalysis or null for utilization actions.")
    action_type: Literal["Reverify", "Train", "Hire", "Reallocate", "Contract"] = Field(description="units=none; uniqueness=not unique; validation=listed action.")
    candidate_employee_id: str | None = Field(default=None, description="units=none; uniqueness=optional foreign key; validation=references Employee.")
    candidate_skill_id: str | None = Field(default=None, description="units=none; uniqueness=optional foreign key; validation=references Skill.")
    source_utilization_id: str | None = Field(default=None, description="units=none; uniqueness=optional foreign key; validation=references Utilization.")
    source_allocation_ids: list[str] = Field(default_factory=list, description="units=none; uniqueness=not unique; validation=source Allocation IDs.")
    rule_id: str = Field(description="units=none; uniqueness=not unique; validation=non-empty rule identifier.")
    owner_actor: Literal["Employee", "Manager", "HR Partner", "IT/Ops Partner", "System Admin"] = Field(description="units=none; uniqueness=not unique; validation=listed accountable actor.")
    status: Literal["Proposed", "Approved", "InProgress", "Done", "Rejected", "Escalated"] = Field(description="units=none; uniqueness=not unique; validation=listed action lifecycle.")
    lead_time_weeks: int = Field(ge=0, description="units=weeks; uniqueness=not unique; validation=non-negative.")
    estimated_cost: float = Field(ge=0, description="units=synthetic currency units; uniqueness=not unique; validation=non-negative.")
    assumptions: str = Field(description="units=none; uniqueness=not unique; validation=documents rule and thresholds.")


TABLE_MODELS: dict[str, type[Row]] = {
    "roles": Role, "skills": Skill, "proficiency_scale": ProficiencyScale,
    "role_skills": RoleSkill, "employees": Employee, "employee_skills": EmployeeSkill,
    "projects": Project, "demand_plans": DemandPlan, "demand_lines": DemandLine,
    "leave": Leave, "holidays": Holiday, "allocations": Allocation, "training": Training,
    "lifecycle_events": LifecycleEvent, "availability": Availability, "utilization": Utilization,
    "supply": Supply, "gap_analysis": GapAnalysis, "gap_actions": GapAction,
}
