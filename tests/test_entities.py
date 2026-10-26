"""Tests for the heater, schedule sensor and schedule calendar entities."""
from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock

from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util.unit_system import METRIC_SYSTEM
import pytest

from custom_components.smart_envi.const import DOMAIN

from .conftest import DEVICE_ID, DEVICE_STATE


def _entity_id(hass: HomeAssistant, platform: str, unique_id: str) -> str:
    entity_id = er.async_get(hass).async_get_entity_id(platform, DOMAIN, unique_id)
    assert entity_id is not None, unique_id
    return entity_id


async def _setup(hass: HomeAssistant, config_entry) -> None:
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()


@pytest.fixture
def celsius_heater(mock_client: AsyncMock) -> AsyncMock:
    """A heater set to Celsius in the Envi app, as all real heaters seen so far are."""
    mock_client.get_device_state.return_value = {
        **DEVICE_STATE,
        "temperature_unit": "C",
        "ambient_temperature": 18,
        "current_temperature": 20,
    }
    return mock_client


async def test_celsius_heater_reports_native_unit(
    hass: HomeAssistant, celsius_heater: AsyncMock, config_entry
) -> None:
    """A °C heater shows its own values, with no round trip through °F."""
    hass.config.units = METRIC_SYSTEM
    await _setup(hass, config_entry)

    state = hass.states.get(_entity_id(hass, "climate", f"{DOMAIN}_{DEVICE_ID}"))
    assert state.attributes["current_temperature"] == 18
    assert state.attributes["temperature"] == 20
    assert state.attributes["min_temp"] == 10
    assert state.attributes["max_temp"] == 30


async def test_celsius_heater_set_temperature_sends_whole_degrees(
    hass: HomeAssistant, celsius_heater: AsyncMock, config_entry
) -> None:
    hass.config.units = METRIC_SYSTEM
    await _setup(hass, config_entry)
    entity_id = _entity_id(hass, "climate", f"{DOMAIN}_{DEVICE_ID}")

    await hass.services.async_call(
        "climate", "set_temperature", {"entity_id": entity_id, "temperature": 21}, blocking=True
    )
    celsius_heater.set_temperature.assert_awaited_once_with(DEVICE_ID, 21)


async def test_offline_heater_is_unavailable(
    hass: HomeAssistant, mock_client: AsyncMock, config_entry
) -> None:
    """When Envi says the heater is offline its last-known values aren't shown as current."""
    mock_client.get_device_state.return_value = {**DEVICE_STATE, "device_status": 0}
    await _setup(hass, config_entry)

    climate = hass.states.get(_entity_id(hass, "climate", f"{DOMAIN}_{DEVICE_ID}"))
    assert climate.state == STATE_UNAVAILABLE
    online = hass.states.get(_entity_id(hass, "binary_sensor", f"{DOMAIN}_{DEVICE_ID}_online"))
    assert online.state == "off"


async def test_next_schedule_change_sensor(
    hass: HomeAssistant, mock_client: AsyncMock, config_entry
) -> None:
    await _setup(hass, config_entry)

    state = hass.states.get(_entity_id(hass, "sensor", f"{DOMAIN}_{DEVICE_ID}_next_schedule_change"))
    assert datetime.fromisoformat(state.state) == datetime.fromisoformat("2026-10-12T01:00:00+00:00")
    assert state.attributes["title"] == "Overnight"
    assert state.attributes["temperature"] == 62


async def test_next_schedule_change_empty_when_schedule_inactive(
    hass: HomeAssistant, mock_client: AsyncMock, config_entry
) -> None:
    mock_client.get_device_state.return_value = {**DEVICE_STATE, "is_schedule_active": False}
    await _setup(hass, config_entry)

    state = hass.states.get(_entity_id(hass, "sensor", f"{DOMAIN}_{DEVICE_ID}_next_schedule_change"))
    assert state.state == "unknown"


async def test_schedule_calendar(
    hass: HomeAssistant, mock_client: AsyncMock, config_entry, freezer
) -> None:
    """The calendar shows the period in progress and lists the week's events."""
    freezer.move_to("2026-10-12T12:00:00-04:00")  # Monday noon in Toronto
    await _setup(hass, config_entry)
    entity_id = _entity_id(hass, "calendar", f"{DOMAIN}_{DEVICE_ID}_schedule_calendar")

    state = hass.states.get(entity_id)
    assert state.state == "on"  # Sunday's overnight setpoint is still in effect
    assert state.attributes["message"] == "Overnight · 62°F"
    assert state.attributes["schedule_name"] == "Main Floor"

    response = await hass.services.async_call(
        "calendar",
        "get_events",
        {
            "entity_id": entity_id,
            "start_date_time": "2026-10-12T00:00:00-04:00",
            "end_date_time": "2026-10-13T00:00:00-04:00",
        },
        blocking=True,
        return_response=True,
    )
    events = response[entity_id]["events"]
    assert [(e["summary"], e["start"], e["end"]) for e in events] == [
        ("Overnight · 62°F", "2026-10-11T21:00:00-04:00", "2026-10-12T19:00:00-04:00"),
        ("Evenings · 68°F", "2026-10-12T19:00:00-04:00", "2026-10-12T21:00:00-04:00"),
        ("Overnight · 62°F", "2026-10-12T21:00:00-04:00", "2026-10-13T19:00:00-04:00"),
    ]


async def test_schedules_fetched_once_per_interval(
    hass: HomeAssistant, mock_client: AsyncMock, config_entry
) -> None:
    """Device polls don't re-fetch the schedule list every time."""
    await _setup(hass, config_entry)
    coordinator = hass.data[DOMAIN][f"{DOMAIN}_coordinator_{config_entry.entry_id}"]

    await coordinator.async_refresh()
    await coordinator.async_refresh()
    assert mock_client.get_schedule_list.await_count == 1
