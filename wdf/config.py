from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


ROOT = Path(__file__).resolve().parents[1]


class Thresholds(BaseModel):
    low_gap_fte: float = Field(ge=0)
    medium_gap_fte: float = Field(ge=0)
    high_utilization: float = Field(ge=0, le=1)
    over_utilization: float = Field(ge=0)
    contract_utilization: float = Field(ge=0)
    contract_budget_cap: float = Field(ge=0)
    contract_cost_per_excess_hour: float = Field(ge=0)
    stale_rate_min: float = Field(ge=0, le=1)
    stale_rate_max: float = Field(ge=0, le=1)
    headcount_budget: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_utilization_thresholds(self) -> Thresholds:
        if self.high_utilization > self.over_utilization:
            raise ValueError("high_utilization must not exceed over_utilization")
        if self.over_utilization >= self.contract_utilization:
            raise ValueError("contract_utilization must exceed over_utilization")
        return self


class AllocationRealism(BaseModel):
    minimum_allocations_per_employee: float = Field(gt=1)
    shared_overlap_employee_share: float = Field(gt=0, le=1)
    minimum_duration_days: int = Field(ge=1)
    maximum_duration_days: int = Field(ge=1)
    allocation_percentages: list[float] = Field(min_length=1)
    shared_overlap_allocation_percentage: float = Field(gt=0, le=1)


class LeaveRealism(BaseModel):
    employee_share: float = Field(gt=0, le=1)
    full_week_records_per_employee: int = Field(ge=1)
    short_records_per_employee: int = Field(ge=0)
    month_weights: list[float] = Field(min_length=12, max_length=12)
    full_week_days: int = Field(ge=1, le=7)
    short_leave_days: list[int] = Field(min_length=1)
    short_leave_attempts: int = Field(ge=1)


class DemandCurves(BaseModel):
    zero_demand_probability: float = Field(ge=0, le=1)
    profile_weights: dict[str, float]
    ramp_start_factor: float = Field(gt=0, le=1)
    ramp_end_factor: float = Field(gt=0, le=1)
    minimum_lines_per_week: int = Field(ge=1)
    maximum_lines_per_week: int = Field(ge=1)
    minimum_required_fte: float = Field(gt=0)
    maximum_required_fte: float = Field(gt=0)
    minimum_creation_lead_days: int = Field(ge=0)
    maximum_creation_lead_days: int = Field(ge=0)
    revision_count: int = Field(ge=0)
    revision_multiplier: float = Field(gt=0)


class WorkCalendar(BaseModel):
    weekly_hours: float = Field(gt=0)
    workday_hours: float = Field(gt=0)
    workdays_per_week: int = Field(ge=1, le=7)

    @model_validator(mode="after")
    def weekly_hours_reconcile(self) -> WorkCalendar:
        expected = self.workday_hours * self.workdays_per_week
        if abs(self.weekly_hours - expected) > 1e-8:
            raise ValueError("weekly_hours must equal workday_hours times workdays_per_week")
        return self


class MasterGeneration(BaseModel):
    hire_lookback_days: int = Field(ge=0)
    fte_values: list[float] = Field(min_length=1)
    fte_probabilities: list[float] = Field(min_length=1)
    skill_validity_months: list[int] = Field(min_length=1)
    role_skill_count_min: int = Field(ge=1)
    role_skill_count_max: int = Field(ge=1)
    role_skill_min_proficiency: int = Field(ge=1)
    role_skill_max_proficiency: int = Field(ge=1)
    role_skill_importance_min: float
    role_skill_importance_max: float
    skill_popularity_exponent: float = Field(gt=0)
    employee_skill_count_min: int = Field(ge=1)
    employee_skill_zipf_shape: float = Field(gt=1)
    stale_skill_rate: float = Field(ge=0, le=1)
    stale_verification_min_days: int = Field(ge=0)
    stale_verification_max_days: int = Field(ge=0)
    current_verification_days_per_month: int = Field(ge=1)
    proficiency_values: list[int] = Field(min_length=1)
    proficiency_probabilities: list[float] = Field(min_length=1)
    project_start_max_offset_days: int = Field(ge=0)
    project_duration_log_mean: float
    project_duration_log_sigma: float = Field(gt=0)
    project_duration_min_days: int = Field(ge=1)
    project_duration_max_days: int = Field(ge=1)
    project_staffing_models: list[str] = Field(min_length=1)
    project_staffing_probabilities: list[float] = Field(min_length=1)
    project_priorities: list[str] = Field(min_length=1)
    project_priority_probabilities: list[float] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_distributions(self) -> MasterGeneration:
        distributions = (
            (self.fte_values, self.fte_probabilities, "fte"),
            (self.proficiency_values, self.proficiency_probabilities, "proficiency"),
            (
                self.project_staffing_models,
                self.project_staffing_probabilities,
                "project staffing",
            ),
            (self.project_priorities, self.project_priority_probabilities, "project priority"),
        )
        for values, probabilities, name in distributions:
            if (
                len(values) != len(probabilities)
                or any(probability < 0 for probability in probabilities)
                or abs(sum(probabilities) - 1.0) > 1e-8
            ):
                raise ValueError(f"{name} probabilities must match values and sum to one")
        return self


class TrainingGeneration(BaseModel):
    employee_count_divisor: int = Field(ge=1)
    minimum_records: int = Field(ge=1)
    employee_index_multiplier: int = Field(ge=1)
    skill_index_multiplier: int = Field(ge=1)
    start_day_multiplier: int = Field(ge=1)
    start_day_modulus: int = Field(ge=1)
    minimum_target_proficiency: int = Field(ge=1)
    maximum_target_proficiency: int = Field(ge=1)
    minimum_cost: float = Field(ge=0)
    maximum_cost: float = Field(ge=0)
    minimum_duration_days: int = Field(ge=1)
    maximum_duration_days: int = Field(ge=1)


class AnomalyGeneration(BaseModel):
    allocation_percentage: float = Field(gt=1)
    dedicated_allocation_max_percentage: float = Field(gt=0, le=1)
    near_miss_shared_extra_percentage: float = Field(gt=0, le=1)
    overlap_anomaly_extra_percentage: float = Field(gt=0, le=1)
    boundary_allocation_week: int = Field(ge=1, le=53)


class ActionPolicy(BaseModel):
    minimum_candidate_proficiency: int = Field(ge=1)
    hire_lead_time_weeks: int = Field(ge=0)
    training_lead_time_weeks: int = Field(ge=0)
    reverification_lead_time_weeks: int = Field(ge=0)
    utilization_action_lead_time_weeks: int = Field(ge=0)
    hire_cost_per_fte: float = Field(ge=0)
    other_gap_action_cost_per_fte: float = Field(ge=0)


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    as_of: date
    seed: int
    anomaly_rate: float = Field(ge=0, le=1)
    thresholds: Thresholds
    work_calendar: WorkCalendar
    master_generation: MasterGeneration
    training_generation: TrainingGeneration
    anomaly_generation: AnomalyGeneration
    action_policy: ActionPolicy
    holidays: list[date]
    allocation_realism: AllocationRealism
    leave_realism: LeaveRealism
    demand_curves: DemandCurves
    forecast: dict[str, Any]


class Scale(BaseModel):
    employees: int = Field(gt=0)
    skills: int = Field(gt=0)
    projects: int = Field(gt=0)
    roles: int = Field(gt=0)


def load_settings(path: Path | None = None) -> Settings:
    config_path = path or ROOT / "config" / "default.yaml"
    with config_path.open(encoding="utf-8") as file:
        return Settings.model_validate(yaml.safe_load(file))


def load_scale(name: str) -> Scale:
    if name not in {"starter", "full"}:
        raise ValueError(f"Unknown scale: {name}")
    path = ROOT / "config" / f"scale_{name}.yaml"
    with path.open(encoding="utf-8") as file:
        return Scale.model_validate(yaml.safe_load(file))
