"""Tests for expanding Envi weekly schedules into dated events."""
from __future__ import annotations

from datetime import UTC, datetime, time
from zoneinfo import ZoneInfo

from custom_components.smart_envi.schedule import events_between, weekly_events

from .conftest import SCHEDULE

TORONTO = ZoneInfo("America/Toronto")


def _local(*args: int) -> datetime:
    return datetime(*args, tzinfo=TORONTO)


def test_weekly_events_flatten_groups() -> None:
    """Five weekdays x 2 events + two weekend days x 2 events, sorted by day and time."""
    events = weekly_events(SCHEDULE)
    assert len(events) == 14
    assert [(e.weekday, e.start, e.title, e.temperature) for e in events[:2]] == [
        (0, time(19, 0), "Evenings", 68.0),
        (0, time(21, 0), "Overnight", 62.0),
    ]
    # Uses heat_to, not the always-zero "temperature" field
    assert all(e.temperature in (62.0, 68.0) for e in events)


def test_events_on_a_weekday() -> None:
    """Monday 12 Oct 2026: Sunday's overnight runs into Monday evening."""
    events = events_between(SCHEDULE, _local(2026, 10, 12), _local(2026, 10, 13), UTC)
    assert [(e.title, e.start, e.end, e.temperature) for e in events] == [
        ("Overnight", _local(2026, 10, 11, 21), _local(2026, 10, 12, 19), 62.0),
        ("Evenings", _local(2026, 10, 12, 19), _local(2026, 10, 12, 21), 68.0),
        ("Overnight", _local(2026, 10, 12, 21), _local(2026, 10, 13, 19), 62.0),
    ]


def test_weekday_to_weekend_transition() -> None:
    """Friday's overnight lasts until Saturday's 07:00 morning event."""
    events = events_between(SCHEDULE, _local(2026, 10, 17, 3), _local(2026, 10, 17, 4), UTC)
    assert [(e.title, e.start, e.end) for e in events] == [
        ("Overnight", _local(2026, 10, 16, 21), _local(2026, 10, 17, 7)),
    ]


def test_single_weekly_event_lasts_a_week() -> None:
    schedule = {
        "timezone": "America/Toronto",
        "schedule_data": [
            {"monday": True, "events": [{"local_time": "08:00", "heat_to": 20, "title": "Week"}]}
        ],
    }
    events = events_between(schedule, _local(2026, 10, 14), _local(2026, 10, 15), UTC)
    assert [(e.start, e.end) for e in events] == [
        (_local(2026, 10, 12, 8), _local(2026, 10, 19, 8)),
    ]


def test_unknown_timezone_uses_default() -> None:
    schedule = {**SCHEDULE, "timezone": "Not/AZone"}
    events = events_between(schedule, _local(2026, 10, 12, 12), _local(2026, 10, 12, 13), UTC)
    assert events[0].start.tzinfo == UTC


def test_empty_or_malformed_schedule() -> None:
    start, end = _local(2026, 10, 12), _local(2026, 10, 13)
    assert events_between({}, start, end, UTC) == []
    assert events_between({"schedule_data": [{"monday": True, "events": [{"title": "x"}]}]}, start, end, UTC) == []
