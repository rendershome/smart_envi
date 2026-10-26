"""Tests for setting up and unloading the Smart Envi integration."""
from __future__ import annotations

from unittest.mock import AsyncMock

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util.unit_system import US_CUSTOMARY_SYSTEM

from custom_components.smart_envi.api import EnviAuthenticationError
from custom_components.smart_envi.const import DOMAIN

from .conftest import DEVICE_ID


async def test_setup_creates_entities(
    hass: HomeAssistant, mock_client: AsyncMock, config_entry
) -> None:
    """Setting up an entry creates the heater and its sensors."""
    hass.config.units = US_CUSTOMARY_SYSTEM
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.LOADED

    entity_id = er.async_get(hass).async_get_entity_id(
        "climate", DOMAIN, f"{DOMAIN}_{DEVICE_ID}"
    )
    assert entity_id is not None
    climate = hass.states.get(entity_id)
    assert climate is not None
    assert climate.state == "heat"
    assert climate.attributes["current_temperature"] == 68
    assert climate.attributes["temperature"] == 72

    for service in ("refresh_all", "get_schedule", "get_status", "test_connection"):
        assert hass.services.has_service(DOMAIN, service)
    # Saving schedules isn't supported by the API (schedule/{id} is a 404)
    assert not hass.services.has_service(DOMAIN, "set_schedule")


async def test_heater_entity_uses_device_name(
    hass: HomeAssistant, mock_client: AsyncMock, config_entry
) -> None:
    """The heater is named after the device once, not twice."""
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    entity_id = er.async_get(hass).async_get_entity_id(
        "climate", DOMAIN, f"{DOMAIN}_{DEVICE_ID}"
    )
    assert entity_id == "climate.living_room"
    assert hass.states.get(entity_id).attributes["friendly_name"] == "Living Room"


async def test_setup_auth_failure_starts_reauth(
    hass: HomeAssistant, mock_client: AsyncMock, config_entry
) -> None:
    """Bad credentials put the entry into the setup error state."""
    mock_client.authenticate.side_effect = EnviAuthenticationError
    config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.SETUP_ERROR


async def test_unload(hass: HomeAssistant, mock_client: AsyncMock, config_entry) -> None:
    """Unloading the entry unloads the platforms."""
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.NOT_LOADED
