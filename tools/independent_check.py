import csv
import datetime
import re
import sqlite3
import sys


TABLES = (
    "roles", "skills", "proficiency_scale", "role_skills", "employees", "employee_skills",
    "projects", "demand_plans", "demand_lines", "leave", "holidays", "allocations",
    "training", "lifecycle_events", "availability", "utilization", "supply",
    "gap_analysis", "gap_actions",
)
PRIMARY_KEYS = {
    "roles": ("role_id",), "skills": ("skill_id",), "proficiency_scale": ("proficiency",),
    "role_skills": ("role_skill_id",), "employees": ("employee_id",),
    "employee_skills": ("employee_skill_id",), "projects": ("project_id",),
    "demand_plans": ("demand_id",), "demand_lines": ("demand_line_id",),
    "leave": ("leave_id",), "holidays": ("holiday_date",), "allocations": ("allocation_id",),
    "training": ("training_id",), "lifecycle_events": ("event_id",),
    "availability": ("availability_id",), "utilization": ("utilization_id",),
    "supply": ("iso_week", "role_id", "skill_id"), "gap_analysis": ("gap_id",),
    "gap_actions": ("gap_action_id",),
}
FOREIGN_KEYS = {
    "role_skills": (("role_id", "roles", "role_id"), ("skill_id", "skills", "skill_id")),
    "employees": (("role_id", "roles", "role_id"), ("manager_id", "employees", "employee_id")),
    "employee_skills": (("employee_id", "employees", "employee_id"), ("skill_id", "skills", "skill_id")),
    "demand_plans": (("project_id", "projects", "project_id"),),
    "demand_lines": (
        ("demand_id", "demand_plans", "demand_id"), ("project_id", "projects", "project_id"),
        ("role_id", "roles", "role_id"), ("skill_id", "skills", "skill_id"),
        ("supersedes_line_id", "demand_lines", "demand_line_id"),
    ),
    "leave": (("employee_id", "employees", "employee_id"),),
    "allocations": (
        ("employee_id", "employees", "employee_id"), ("project_id", "projects", "project_id"),
        ("role_id", "roles", "role_id"), ("skill_basis_esk_id", "employee_skills", "employee_skill_id"),
    ),
    "training": (("employee_id", "employees", "employee_id"), ("skill_id", "skills", "skill_id")),
    "availability": (("employee_id", "employees", "employee_id"),),
    "utilization": (("employee_id", "employees", "employee_id"),),
    "supply": (("role_id", "roles", "role_id"), ("skill_id", "skills", "skill_id")),
    "gap_analysis": (("role_id", "roles", "role_id"), ("skill_id", "skills", "skill_id")),
    "gap_actions": (
        ("gap_id", "gap_analysis", "gap_id"), ("candidate_employee_id", "employees", "employee_id"),
        ("candidate_skill_id", "skills", "skill_id"),
        ("source_utilization_id", "utilization", "utilization_id"),
    ),
}
ENUMS = {
    ("roles", "family"): {"Engineering", "Data", "QA", "Design", "PM", "DevOps", "Security", "Support"},
    ("skills", "category"): {"Technical", "Domain", "Leadership", "Platform", "Compliance"},
    ("employees", "employment_type"): {"FT", "PT"},
    ("employees", "status"): {"Active", "Inactive"},
    ("employee_skills", "currency_flag"): {"Current", "Stale"},
    ("projects", "priority"): {"Low", "Medium", "High", "Critical"},
    ("projects", "staffing_model"): {"Shared-Pool", "Dedicated-Team"},
    ("projects", "status"): {"Planned", "Active", "Completed", "Cancelled"},
    ("demand_lines", "source"): {"PlanTool", "ResourceRequest"},
    ("demand_lines", "status"): {"Draft", "Approved", "Superseded"},
    ("leave", "leave_type"): {"Annual", "Sick", "Care", "Other"},
    ("leave", "status"): {"Approved", "Pending", "Rejected"},
    ("allocations", "status"): {"Proposed", "Active", "Completed", "Cancelled"},
    ("training", "status"): {"Planned", "Enrolled", "Completed", "Failed", "Cancelled"},
    ("gap_analysis", "risk_level"): {"Covered", "Low", "Medium", "High"},
    ("gap_actions", "action_type"): {"Reverify", "Train", "Hire", "Reallocate", "Contract"},
    ("gap_actions", "owner_actor"): {"Employee", "Manager", "HR Partner", "IT/Ops Partner", "System Admin"},
    ("gap_actions", "status"): {"Proposed", "Approved", "InProgress", "Done", "Rejected", "Escalated"},
    ("lifecycle_events", "entity_type"): {"Employee", "Project", "Allocation", "Training", "DemandLine"},
}
ID_PATTERNS = {
    ("roles", "role_id"): r"ROLE-\d{4}", ("skills", "skill_id"): r"SKL-\d{6}",
    ("employees", "employee_id"): r"EMP-\d{6}", ("projects", "project_id"): r"PRJ-2026-\d{6}",
    ("role_skills", "role_skill_id"): r"RS-ROLE-\d{4}-\d{6}",
    ("employee_skills", "employee_skill_id"): r"ESK-\d{6}",
    ("demand_plans", "demand_id"): r"DEM-PRJ-2026-\d{6}-2026W\d{2}",
    ("demand_lines", "demand_line_id"): r"DEML-\d{6}",
    ("leave", "leave_id"): r"LEAVE-\d{6}", ("allocations", "allocation_id"): r"ALLOC-2026-\d{6}",
    ("training", "training_id"): r"TRN-\d{6}", ("lifecycle_events", "event_id"): r"EVT-\d{6}",
    ("availability", "availability_id"): r"AVL-\d{6}",
    ("utilization", "utilization_id"): r"UTL-\d{6}-2026W\d{2}",
    ("gap_analysis", "gap_id"): r"GAP-2026W\d{2}-\d{6}",
    ("gap_actions", "gap_action_id"): r"GACT-\d{6}",
}
AS_OF = datetime.date(2026, 10, 22)
EPSILON = 0.00011
FORECAST_EPSILON = 0.00000001


def fail(message):
    ERRORS.append(message)


def read_csv(root, table):
    with open(root + "/" + table + ".csv", encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def number(row, field):
    return float(row[field]) if row[field] else 0.0


def parse_ids(value):
    if not value or not re.fullmatch(r'\[(?:"[A-Z0-9-]+"(?:,"[A-Z0-9-]+")*)?\]', value):
        fail("Malformed ID list in CSV: " + value[:100])
        return []
    return re.findall(r'"([A-Z0-9-]+)"', value)


def close(left, right):
    return abs(left - right) <= EPSILON


def main(root):
    global ERRORS
    ERRORS = []
    data = {table: read_csv(root, table) for table in TABLES}
    print("Independent stdlib CSV audit (no imports from wdf)")

    for table, fields in PRIMARY_KEYS.items():
        keys = [tuple(row[field] for field in fields) for row in data[table]]
        if len(keys) != len(set(keys)):
            fail(table + " primary key is not unique")
    print("PASS PK uniqueness for {} tables".format(len(PRIMARY_KEYS)))

    for source, relations in FOREIGN_KEYS.items():
        for field, target, target_field in relations:
            target_values = {row[target_field] for row in data[target]}
            missing = [row[field] for row in data[source] if row[field] and row[field] not in target_values]
            if missing:
                fail("{}.{}, missing {} reference(s)".format(source, field, len(missing)))
    allocation_by_id = {row["allocation_id"]: row for row in data["allocations"]}
    utilization_by_id = {row["utilization_id"]: row for row in data["utilization"]}
    for action in data["gap_actions"]:
        allocation_ids = parse_ids(action["source_allocation_ids"])
        if any(allocation_id not in allocation_by_id for allocation_id in allocation_ids):
            fail("GapAction references a missing Allocation")
        if action["source_utilization_id"]:
            utilization = utilization_by_id[action["source_utilization_id"]]
            if utilization["employee_id"] != action["candidate_employee_id"]:
                fail("GapAction employee does not match source Utilization")
            week = utilization["iso_week"]
            week_start = datetime.date.fromisocalendar(2026, int(week[-2:]), 1)
            week_end = week_start + datetime.timedelta(days=6)
            for allocation_id in allocation_ids:
                allocation = allocation_by_id[allocation_id]
                if (
                    allocation["employee_id"] != utilization["employee_id"]
                    or allocation["status"] not in {"Proposed", "Active"}
                    or datetime.date.fromisoformat(allocation["start_date"]) > week_end
                    or datetime.date.fromisoformat(allocation["end_date"]) < week_start
                ):
                    fail("GapAction source Allocation does not reconcile to source Utilization")
    entity_tables = {
        "Employee": ("employees", "employee_id"), "Project": ("projects", "project_id"),
        "Allocation": ("allocations", "allocation_id"), "Training": ("training", "training_id"),
        "DemandLine": ("demand_lines", "demand_line_id"),
    }
    for event in data["lifecycle_events"]:
        table, field = entity_tables[event["entity_type"]]
        if event["entity_id"] not in {row[field] for row in data[table]}:
            fail("Lifecycle event references missing " + event["entity_id"])
    print("PASS CSV foreign keys and lifecycle entity references")

    for (table, field), allowed in ENUMS.items():
        invalid = [row[field] for row in data[table] if row[field] not in allowed]
        if invalid:
            fail("{}.{}, invalid enum {}".format(table, field, invalid[0]))
    for (table, field), pattern in ID_PATTERNS.items():
        if any(not re.fullmatch(pattern, row[field]) for row in data[table]):
            fail(table + "." + field + " has invalid ID format")
    for table, rows in data.items():
        for row in rows:
            if "iso_week" in row and row["iso_week"]:
                match = re.fullmatch(r"2026W(\d{2})", row["iso_week"])
                if not match:
                    fail(table + " has malformed ISO week " + row["iso_week"])
                else:
                    try:
                        datetime.date.fromisocalendar(2026, int(match.group(1)), 1)
                    except ValueError:
                        fail(table + " has invalid ISO week " + row["iso_week"])
            for field, value in row.items():
                if field.endswith("_date") and value:
                    try:
                        datetime.date.fromisoformat(value)
                    except ValueError:
                        fail(table + "." + field + " is not an ISO date")
    print("PASS enum, exact ID regex, ISO-week, and date-format checks")

    date_pairs = (
        ("projects", "start_date", "end_date"), ("allocations", "start_date", "end_date"),
        ("leave", "start_date", "end_date"), ("training", "start_date", "end_date"),
        ("employee_skills", "last_verified_date", "expiry_date"),
    )
    for table, start_field, end_field in date_pairs:
        if any(datetime.date.fromisoformat(row[start_field]) > datetime.date.fromisoformat(row[end_field])
               for row in data[table]):
            fail(table + " has reversed dates")
    for row in data["demand_plans"]:
        year, week = map(int, re.fullmatch(r"(\d{4})W(\d{2})", row["iso_week"]).groups())
        if datetime.date.fromisoformat(row["week_start"]) != datetime.date.fromisocalendar(year, week, 1):
            fail("Demand plan week_start does not match " + row["demand_id"])
    print("PASS date ordering and demand-week date agreement")

    employee_by_id = {row["employee_id"]: row for row in data["employees"]}
    availability_by_key = {}
    weekly_capacity = {}
    weekly_hour_values = {
        round(
            number(row, "capacity_hours")
            / number(employee_by_id[row["employee_id"]], "fte"),
            8,
        )
        for row in data["availability"]
        if number(employee_by_id[row["employee_id"]], "fte") > 0
    }
    if len(weekly_hour_values) != 1:
        fail("Employee capacity does not use a consistent weekly-hours setting")
    weekly_hours = next(iter(weekly_hour_values))
    for row in data["availability"]:
        key = (row["employee_id"], row["iso_week"])
        availability_by_key[key] = row
        expected_employee_capacity = (
            number(employee_by_id[row["employee_id"]], "fte") * weekly_hours
        )
        if not close(number(row, "capacity_hours"), expected_employee_capacity):
            fail("Employee capacity mismatch at " + row["availability_id"])
        expected = number(row, "capacity_hours") - number(row, "leave_hours") - number(row, "holiday_hours")
        if not close(number(row, "available_hours"), expected):
            fail("Available hours arithmetic mismatch at " + row["availability_id"])
        weekly_capacity[row["iso_week"]] = weekly_capacity.get(row["iso_week"], 0.0) + number(row, "capacity_hours")
    expected_capacity = sum(
        number(employee, "fte") * weekly_hours for employee in data["employees"]
    )
    if len(weekly_capacity) != 53 or set(weekly_capacity) != {
        "2026W{:02d}".format(week) for week in range(1, 54)
    }:
        fail("Availability does not cover all 53 ISO weeks")
    if any(not close(capacity, expected_capacity) for capacity in weekly_capacity.values()):
        fail("Weekly capacity does not reconcile to employee FTE")
    print("PASS availability arithmetic and capacity reconciliation: 53 weeks")

    allocations_by_employee = {}
    for row in data["allocations"]:
        if row["status"] in {"Proposed", "Active"}:
            allocations_by_employee.setdefault(row["employee_id"], []).append(row)
    utilization_by_key = {}
    for row in data["utilization"]:
        key = (row["employee_id"], row["iso_week"])
        utilization_by_key[key] = row
        availability = availability_by_key[key]
        week_start = datetime.date.fromisocalendar(2026, int(row["iso_week"][-2:]), 1)
        week_end = week_start + datetime.timedelta(days=6)
        applicable = [
            item for item in allocations_by_employee.get(row["employee_id"], [])
            if datetime.date.fromisoformat(item["start_date"]) <= week_end
            and datetime.date.fromisoformat(item["end_date"]) >= week_start
        ]
        pct = sum(number(item, "allocation_pct") for item in applicable)
        hours = pct * number(availability, "available_hours")
        available = number(availability, "available_hours")
        capacity = number(availability, "capacity_hours")
        util_available = hours / available if available else None
        util_capacity = hours / capacity if capacity else None
        if not close(number(row, "allocation_pct_sum"), pct):
            fail("Utilization percentage mismatch at " + row["utilization_id"])
        if not close(number(row, "allocated_hours"), hours):
            fail("Allocated hours mismatch at " + row["utilization_id"])
        for field, expected in (("utilization_available", util_available), ("utilization_capacity", util_capacity)):
            actual = float(row[field]) if row[field] else None
            if actual is None and expected is not None or actual is not None and (expected is None or not close(actual, expected)):
                fail(field + " mismatch at " + row["utilization_id"])
    print("PASS utilization recompute for {} employee-weeks".format(len(data["utilization"])))

    lines_by_key = {}
    for row in data["demand_lines"]:
        if row["status"] == "Approved":
            key = (row["iso_week"], row["role_id"], row["skill_id"])
            lines_by_key.setdefault(key, []).append(row)
    skills_by_employee = {}
    for row in data["employee_skills"]:
        employee = employee_by_id[row["employee_id"]]
        skills_by_employee.setdefault((employee["role_id"], row["skill_id"]), []).append(row)
    gap_rows = data["gap_analysis"]
    if len(gap_rows) < 1000:
        fail("Need at least 1,000 gap rows to satisfy the independent sample threshold")
    sample = [gap_rows[(index * len(gap_rows)) // 1000] for index in range(1000)]
    for gap in sample:
        key = (gap["iso_week"], gap["role_id"], gap["skill_id"])
        source_lines = lines_by_key.get(key, [])
        linked_ids = parse_ids(gap["source_demand_line_ids"])
        expected_line_ids = sorted(row["demand_line_id"] for row in source_lines)
        if linked_ids != expected_line_ids:
            fail("Gap demand-line trace mismatch at " + gap["gap_id"])
        minimum = min((int(row["min_proficiency"]) for row in source_lines), default=0)
        eligible = [
            skill for skill in skills_by_employee.get((gap["role_id"], gap["skill_id"]), [])
            if int(skill["proficiency"]) >= minimum
            and skill["currency_flag"] == "Current"
            and datetime.date.fromisoformat(skill["expiry_date"]) >= AS_OF
        ]
        expected_supply = sum(
            number(availability_by_key[(skill["employee_id"], gap["iso_week"])], "available_hours")
            for skill in eligible
        ) / weekly_hours
        demand = sum(number(row, "required_fte") for row in source_lines)
        if not close(number(gap, "demand_fte"), round(demand, 4)):
            fail("Gap demand recompute mismatch at " + gap["gap_id"])
        if not close(number(gap, "supply_fte"), round(expected_supply, 4)):
            fail("Gap supply recompute mismatch at " + gap["gap_id"])
        if not close(number(gap, "gap_fte"), round(demand, 4) - round(expected_supply, 4)):
            fail("Gap arithmetic mismatch at " + gap["gap_id"])
        supporting = parse_ids(gap["supporting_esk_ids"])
        eligible_ids = {row["employee_skill_id"] for row in eligible}
        if set(supporting) != eligible_ids:
            fail("Gap supporting-skill trace mismatch at " + gap["gap_id"])
    print("PASS demand/supply/gap recompute and traces for {} stratified gaps".format(len(sample)))

    current_state = {}
    for event in data["lifecycle_events"]:
        key = (event["entity_type"], event["entity_id"])
        if event["from_state"] != current_state.get(key, ""):
            fail("Lifecycle from_state mismatch at " + event["event_id"])
        current_state[key] = event["to_state"]
    current_tables = {
        "Employee": ("employees", "employee_id"), "Project": ("projects", "project_id"),
        "Allocation": ("allocations", "allocation_id"), "Training": ("training", "training_id"),
        "DemandLine": ("demand_lines", "demand_line_id"),
    }
    for entity_type, (table, field) in current_tables.items():
        for row in data[table]:
            if current_state.get((entity_type, row[field])) != row["status"]:
                fail("Latest lifecycle state mismatch for " + row[field])
    print("PASS lifecycle latest state matches current state")

    truth_path = root + "/ground_truth/ground_truth.csv"
    truth_ids = set()
    with open(truth_path, encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            if row["issue_type"] == "DEMAND_DOUBLE_COUNTED":
                truth_ids.add(row["record_id"])
    groups = {}
    for row in data["demand_lines"]:
        if row["status"] == "Approved":
            key = (row["demand_id"], row["role_id"], row["skill_id"])
            groups.setdefault(key, []).append(row["demand_line_id"])
    duplicate_ids = set()
    for values in groups.values():
        if len(values) > 1:
            duplicate_ids.update(sorted(values)[1:])
    if duplicate_ids != truth_ids:
        fail("Approved business-key duplicates differ from injected double-count labels")
    print("PASS approved-demand duplicate groups match injected labels: {}".format(len(duplicate_ids)))

    role_forecasts = read_csv(root, "forecast")
    project_forecasts = read_csv(root, "forecast_project")
    role_forecast_by_key = {}
    for row in role_forecasts:
        key = (row["iso_week"], row["role_id"], row["method"])
        if key in role_forecast_by_key:
            fail("Duplicate role forecast key: " + repr(key))
        role_forecast_by_key[key] = number(row, "forecast_demand_fte")
    project_ids = {row["project_id"] for row in data["projects"]}
    project_forecast_totals = {}
    project_forecast_keys = set()
    for row in project_forecasts:
        project_key = (
            row["project_id"], row["iso_week"], row["role_id"], row["method"]
        )
        if project_key in project_forecast_keys:
            fail("Duplicate project forecast key: " + repr(project_key))
        project_forecast_keys.add(project_key)
        if row["project_id"] not in project_ids:
            fail("Project forecast references missing Project " + row["project_id"])
        role_key = (row["iso_week"], row["role_id"], row["method"])
        project_forecast_totals[role_key] = (
            project_forecast_totals.get(role_key, 0.0)
            + number(row, "predicted_fte")
        )
    if set(project_forecast_totals) - set(role_forecast_by_key):
        fail("Project forecast contains keys without a role forecast")
    for key, role_total in role_forecast_by_key.items():
        project_total = project_forecast_totals.get(key, 0.0)
        if abs(role_total - project_total) > FORECAST_EPSILON:
            fail("Project forecast does not reconcile to role forecast at " + repr(key))
    print(
        "PASS project/role forecast reconciliation: {} role forecast rows, {} project rows".format(
            len(role_forecast_by_key), len(project_forecasts)
        )
    )

    connection = sqlite3.connect(":memory:")
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        with open(root + "/schema.sql", encoding="utf-8") as stream:
            connection.executescript(stream.read())
        with open(root + "/seed.sql", encoding="utf-8") as stream:
            connection.executescript(stream.read())
        foreign_key_errors = list(connection.execute("PRAGMA foreign_key_check"))
        if foreign_key_errors:
            fail("SQLite foreign_key_check reports {}".format(len(foreign_key_errors)))
        for table in TABLES:
            actual = connection.execute('SELECT COUNT(*) FROM "{}"'.format(table)).fetchone()[0]
            if actual != len(data[table]):
                fail("Seed SQL row count differs from CSV for " + table)
    except sqlite3.Error as error:
        fail("Could not load seed SQL into fresh SQLite: " + str(error))
    finally:
        connection.close()
    print("PASS fresh SQLite seed load and PRAGMA foreign_key_check")

    for table in TABLES:
        print("{}: {}".format(table, len(data[table])))
    if ERRORS:
        for error in ERRORS:
            print("FAIL: " + error)
        return 1
    print("RESULT: PASS ({} independent checks)".format(10))
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python tools/independent_check.py DATASET_DIRECTORY")
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
