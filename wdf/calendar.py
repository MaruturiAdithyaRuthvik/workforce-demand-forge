from __future__ import annotations

from datetime import date, timedelta


YEAR = 2026
AS_OF = date(2026, 10, 22)


def iso_weeks(year: int = YEAR) -> list[dict[str, object]]:
    last_week = date(year, 12, 28).isocalendar().week
    return [
        {
            "iso_week": f"{year}W{week:02d}",
            "week_start": date.fromisocalendar(year, week, 1).isoformat(),
            "week_end": date.fromisocalendar(year, week, 7).isoformat(),
        }
        for week in range(1, last_week + 1)
    ]


def add_months(value: date, months: int) -> date:
    month = value.month - 1 + months
    year = value.year + month // 12
    month = month % 12 + 1
    day = min(value.day, (date(year + (month == 12), month % 12 + 1, 1) - timedelta(days=1)).day)
    return date(year, month, day)
