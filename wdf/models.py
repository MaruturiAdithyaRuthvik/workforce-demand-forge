from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Row(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Role(Row):
    role_id: str
    title: str
    family: str


class Skill(Row):
    skill_id: str
    name: str
    category: str
    validity_months: int = Field(ge=1)


class Employee(Row):
    employee_id: str
    role_id: str
    manager_id: str | None
    employment_type: Literal["FT", "PT"]
    fte: float
    hire_date: str
    status: Literal["Active", "Inactive"]


class Project(Row):
    project_id: str
    start_date: str
    end_date: str
    priority: Literal["Low", "Medium", "High", "Critical"]
    staffing_model: Literal["Shared-Pool", "Dedicated-Team"]
    status: Literal["Planned", "Active", "Completed", "Cancelled"]


class DemandLine(Row):
    demand_line_id: str
    demand_id: str
    project_id: str
    iso_week: str
    role_id: str
    skill_id: str
    required_fte: float = Field(gt=0)
    min_proficiency: int = Field(ge=1, le=5)
    source: Literal["PlanTool", "ResourceRequest"]
    created_on: str
    supersedes_line_id: str | None
    status: Literal["Draft", "Approved", "Superseded"]


class Allocation(Row):
    allocation_id: str
    employee_id: str
    project_id: str
    role_id: str
    start_date: str
    end_date: str
    allocation_pct: float = Field(gt=0)
    skill_basis_esk_id: str | None
    status: Literal["Proposed", "Active", "Completed", "Cancelled"]


class Availability(Row):
    availability_id: str
    employee_id: str
    iso_week: str
    capacity_hours: float = Field(ge=0)
    leave_hours: float = Field(ge=0)
    holiday_hours: float = Field(ge=0)
    available_hours: float = Field(ge=0)


TABLE_MODELS: dict[str, type[Row]] = {
    "roles": Role,
    "skills": Skill,
    "employees": Employee,
    "projects": Project,
    "demand_lines": DemandLine,
    "allocations": Allocation,
    "availability": Availability,
}
