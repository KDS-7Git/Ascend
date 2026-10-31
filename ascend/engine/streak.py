from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo


def logical_date(
    now: datetime, timezone: str | None = None, rollover_hour: int = 4
) -> date:
    if timezone:
        if now.tzinfo is None:
            raise ValueError("Timezone conversion requires an aware timestamp")
        now = now.astimezone(ZoneInfo(timezone))
    return (now - timedelta(hours=rollover_hour)).date()


def streak_details(logged: set[date], today: date, freezes_per_week: int = 1):
    count, used = 0, {}
    d = today if today in logged else today - timedelta(days=1)
    while True:
        if d in logged:
            count += 1
        else:
            week = d.isocalendar()[:2]
            isolated = (
                d - timedelta(days=1) in logged and d + timedelta(days=1) in logged
            )
            if isolated and used.get(week, 0) < freezes_per_week:
                used[week] = used.get(week, 0) + 1
            else:
                break
        d -= timedelta(days=1)
    return count, used


def compute_streak(logged: set[date], today: date, freezes_per_week: int = 1) -> int:
    return streak_details(logged, today, freezes_per_week)[0]


def best_streak(logged: set[date], freezes_per_week: int = 1) -> int:
    return max((compute_streak(logged, d, freezes_per_week) for d in logged), default=0)
