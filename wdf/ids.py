def entity_id(prefix: str, number: int, width: int = 6) -> str:
    return f"{prefix}-{number:0{width}d}"


def project_id(number: int) -> str:
    return f"PRJ-2026-{number:06d}"


def allocation_id(number: int) -> str:
    return f"ALLOC-2026-{number:06d}"


def demand_id(project: str, iso_week: str) -> str:
    return f"DEM-{project}-{iso_week}"
