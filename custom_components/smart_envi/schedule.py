"""Expand Envi weekly schedules into dated events.

An Envi schedule (from schedule/list) looks like:

    {
        "id": 7873,
        "name": "Basement",
        "timezone": "America/Toronto",
        "temperature_unit": "C",
        "schedule_data": [
            {
                "monday": true, ..., "sunday": false,
                "events": [
                    {"local_time": "19:00", "heat_to": 20, "title": "Evenings", ...},
                    {"local_time": "21:00", "heat_to": 16, "title": "Overnight", ...},
                ],
            },
            ...
        ],
    }

Each event sets a target temperature that holds until the next event, so an
event's end is the start of the next one in the weekly cycle.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, tzinfo
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


@dataclass(frozen=True)
class WeeklyEvent:
    """One setpoint change in the weekly cycle."""

    weekday: int  # 0 = Monday
    start: time
    title: str
    temperature: float


@dataclass(frozen=True)
class ScheduleEvent:
    """One dated occurrence of a setpoint change."""

    start: datetime
    end: datetime
    title: str
    temperature: float


def schedule_timezone(schedule: dict, default: tzinfo) -> tzinfo:
    """Return the schedule's timezone, falling back to the given default."""
    name = schedule.get("timezone")
    if name:
        try:
            return ZoneInfo(name)
        except (ZoneInfoNotFoundError, ValueError):
            pass
    return default


def _parse_time(value: str | None) -> time | None:
    if not value:
        return None
    try:
        parts = [int(p) for p in str(value).split(":")]
        return time(*parts[:3])
    except (TypeError, ValueError):
        return None


def weekly_events(schedule: dict) -> list[WeeklyEvent]:
    """Flatten a schedule's day groups into a sorted weekly list of events."""
    events: list[WeeklyEvent] = []
    for group in schedule.get("schedule_data") or []:
        if not isinstance(group, dict):
            continue
        days = [i for i, day in enumerate(WEEKDAYS) if group.get(day)]
        for event in group.get("events") or []:
            if not isinstance(event, dict):
                continue
            start = _parse_time(event.get("local_time"))
            temperature = event.get("heat_to")
            if temperature is None:
                temperature = event.get("temperature")
            if start is None or temperature is None:
                continue
            title = event.get("title") or "Scheduled change"
            events.extend(
                WeeklyEvent(day, start, title, float(temperature)) for day in days
            )
    return sorted(events, key=lambda e: (e.weekday, e.start))


def events_between(
    schedule: dict, start: datetime, end: datetime, default_tz: tzinfo
) -> list[ScheduleEvent]:
    """Return dated events that overlap [start, end), in the schedule's timezone."""
    weekly = weekly_events(schedule)
    if not weekly:
        return []
    tz = schedule_timezone(schedule, default_tz)

    # An event can last up to a week (until the next one in the cycle), so
    # generate occurrences from a week before `start` to a week after `end`:
    # that covers the event already in progress at `start` and gives the last
    # event before `end` its successor.
    first_day = start.astimezone(tz).date() - timedelta(days=8)
    last_day = end.astimezone(tz).date() + timedelta(days=8)
    starts: list[tuple[datetime, WeeklyEvent]] = []
    day = first_day
    while day <= last_day:
        for event in weekly:
            if event.weekday == day.weekday():
                starts.append((_at(day, event.start, tz), event))
        day += timedelta(days=1)
    starts.sort(key=lambda item: item[0])

    result: list[ScheduleEvent] = []
    for (event_start, event), (next_start, _) in zip(starts, starts[1:], strict=False):
        if event_start < end and next_start > start:
            result.append(
                ScheduleEvent(event_start, next_start, event.title, event.temperature)
            )
    return result


def _at(day: date, at: time, tz: tzinfo) -> datetime:
    return datetime.combine(day, at, tzinfo=tz)
