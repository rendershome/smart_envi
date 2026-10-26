"""Shared fixtures for Smart Envi tests."""
from __future__ import annotations

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.smart_envi.const import DOMAIN

USERNAME = "user@example.com"
PASSWORD = "test-password"
DEVICE_ID = "12345"

DEVICE_STATE = {
    "id": 12345,
    "name": "Living Room",
    "serial_no": "SN123",
    "model_no": "EH-1",
    "firmware_version": "1.2.3",
    "temperature_unit": "F",
    "ambient_temperature": 68,
    "current_temperature": 72,
    "state": 1,
    "current_mode": 1,
    "status": 1,
    "device_status": 1,
    "signal_strength": -50,
    "ssid": "home",
    "location_name": "Living Room",
    "freeze_protect_setting": False,
    "child_lock_setting": True,
    "is_schedule_active": True,
    "is_hold": False,
    "schedule": {
        "schedule_id": 777,
        "name": "Main Floor",
        "title": "Overnight",
        "temperature": 62,
        "trigger_time": "01:00",
        "day": "monday",
        "eventDate": "2026-10-12T01:00:00.000Z",
    },
}

# Shaped like a real schedule/list entry: weekdays and weekends as two groups.
SCHEDULE = {
    "id": 777,
    "name": "Main Floor",
    "timezone": "America/Toronto",
    "temperature_unit": "F",
    "schedule_data": [
        {
            **{day: True for day in ("monday", "tuesday", "wednesday", "thursday", "friday")},
            "saturday": False,
            "sunday": False,
            "events": [
                {"local_time": "19:00", "heat_to": 68, "cool_to": 68, "temperature": 0, "title": "Evenings"},
                {"local_time": "21:00", "heat_to": 62, "cool_to": 62, "temperature": 0, "title": "Overnight"},
            ],
        },
        {
            **{day: False for day in ("monday", "tuesday", "wednesday", "thursday", "friday")},
            "saturday": True,
            "sunday": True,
            "events": [
                {"local_time": "07:00", "heat_to": 68, "cool_to": 68, "temperature": 0, "title": "Morning"},
                {"local_time": "21:00", "heat_to": 62, "cool_to": 62, "temperature": 0, "title": "Overnight"},
            ],
        },
    ],
}


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Allow Home Assistant to load custom_components/smart_envi."""
    return


@pytest.fixture
def config_entry() -> MockConfigEntry:
    """A config entry for a configured Envi account."""
    return MockConfigEntry(
        domain=DOMAIN,
        title=f"Smart Envi ({USERNAME})",
        unique_id=USERNAME,
        data={"username": USERNAME, "password": PASSWORD},
    )


@pytest.fixture
def mock_client() -> Generator[AsyncMock]:
    """Patch the Envi API client everywhere it is constructed."""
    with (
        patch(
            "custom_components.smart_envi.EnviApiClient", autospec=True
        ) as client_cls,
        patch(
            "custom_components.smart_envi.config_flow.EnviApiClient",
            new=client_cls,
        ),
    ):
        client = client_cls.return_value
        client.authenticate.return_value = None
        client.fetch_all_device_ids.return_value = [DEVICE_ID]
        client.get_device_state.return_value = dict(DEVICE_STATE)
        client.get_schedule_list.return_value = [SCHEDULE]
        client.convert_temperature.side_effect = lambda t, f, to: t
        yield client
