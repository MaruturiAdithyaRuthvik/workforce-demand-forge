from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field


ROOT = Path(__file__).resolve().parents[1]


class Thresholds(BaseModel):
    low_gap_fte: float = Field(ge=0)
    medium_gap_fte: float = Field(ge=0)
    high_utilization: float = Field(ge=0)
    over_utilization: float = Field(ge=0)
    contract_utilization: float = Field(ge=0)
    contract_budget_cap: float = Field(ge=0)
    contract_cost_per_excess_hour: float = Field(ge=0)
    stale_rate_min: float = Field(ge=0, le=1)
    stale_rate_max: float = Field(ge=0, le=1)
    headcount_budget: int = Field(ge=0)


class AllocationRealism(BaseModel):
    minimum_allocations_per_employee: float = Field(gt=1)
    shared_overlap_employee_share: float = Field(gt=0, le=1)


class LeaveRealism(BaseModel):
    employee_share: float = Field(gt=0, le=1)
    full_week_records_per_employee: int = Field(ge=1)
    short_records_per_employee: int = Field(ge=0)
    month_weights: list[float] = Field(min_length=12, max_length=12)


class DemandCurves(BaseModel):
    zero_demand_probability: float = Field(ge=0, le=1)
    profile_weights: dict[str, float]
    ramp_start_factor: float = Field(gt=0, le=1)
    ramp_end_factor: float = Field(gt=0, le=1)


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    as_of: date
    seed: int
    anomaly_rate: float = Field(ge=0, le=1)
    thresholds: Thresholds
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
