"""Tests for setting up and unloading the Smart Envi integration."""
from __future__ import annotations

from unittest.mock import AsyncMock

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.util.unit_system import US_CUSTOMARY_SYSTEM

from custom_components.smart_envi import async_remove_config_entry_device
from custom_components.smart_envi.api import EnviAuthenticationError
from custom_components.smart_envi.const import DOMAIN

from .conftest import DEVICE_ID, SERIAL


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
        "climate", DOMAIN, f"{DOMAIN}_{SERIAL}"
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
        "climate", DOMAIN, f"{DOMAIN}_{SERIAL}"
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


def _register_heater(
    hass: HomeAssistant, config_entry, envi_id: str, object_id: str, **device_kwargs
) -> dr.DeviceEntry:
    """Register a heater device with a climate and an online entity, as an old version did."""
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers={(DOMAIN, envi_id)},
        serial_number=SERIAL,
        name="Living Room",
        **device_kwargs,
    )
    ent_reg = er.async_get(hass)
    for platform, suffix in (("climate", ""), ("binary_sensor", "_online")):
        ent_reg.async_get_or_create(
            platform,
            DOMAIN,
            f"{DOMAIN}_{envi_id}{suffix}",
            config_entry=config_entry,
            device_id=device.id,
            suggested_object_id=f"{object_id}{suffix}",
        )
    return device


async def test_readded_heater_is_merged_into_one_device(
    hass: HomeAssistant, mock_client: AsyncMock, config_entry
) -> None:
    """A heater re-added in the Envi app (new id, same serial) keeps one device and its original entities."""
    config_entry.add_to_hass(hass)
    original = _register_heater(hass, config_entry, "999", "living_room_original")
    _register_heater(hass, config_entry, DEVICE_ID, "living_room_readded")

    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    devices = dr.async_entries_for_config_entry(dr.async_get(hass), config_entry.entry_id)
    assert [d.id for d in devices] == [original.id]
    assert devices[0].identifiers == {(DOMAIN, SERIAL)}

    ent_reg = er.async_get(hass)
    assert ent_reg.async_get_entity_id("climate", DOMAIN, f"{DOMAIN}_{SERIAL}") == (
        "climate.living_room_original"
    )
    assert ent_reg.async_get_entity_id("binary_sensor", DOMAIN, f"{DOMAIN}_{SERIAL}_online") == (
        "binary_sensor.living_room_original_online"
    )
    assert ent_reg.async_get("climate.living_room_readded") is None
    assert hass.states.get("climate.living_room_original").state == "heat"


async def test_disabled_duplicate_is_not_kept(
    hass: HomeAssistant, mock_client: AsyncMock, config_entry
) -> None:
    """When the oldest copy of a heater was disabled, the enabled one is kept."""
    config_entry.add_to_hass(hass)
    _register_heater(
        hass, config_entry, "999", "living_room_old",
        disabled_by=dr.DeviceEntryDisabler.USER,
    )
    current = _register_heater(hass, config_entry, DEVICE_ID, "living_room")

    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    devices = dr.async_entries_for_config_entry(dr.async_get(hass), config_entry.entry_id)
    assert [d.id for d in devices] == [current.id]
    assert er.async_get(hass).async_get_entity_id("climate", DOMAIN, f"{DOMAIN}_{SERIAL}") == (
        "climate.living_room"
    )


async def test_entity_from_disabled_duplicate_is_reenabled(
    hass: HomeAssistant, mock_client: AsyncMock, config_entry
) -> None:
    """An entity that only existed on a disabled copy of the heater moves over enabled."""
    config_entry.add_to_hass(hass)
    _register_heater(hass, config_entry, "999", "living_room")
    readded = dr.async_get(hass).async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers={(DOMAIN, DEVICE_ID)},
        serial_number=SERIAL,
        disabled_by=dr.DeviceEntryDisabler.USER,
    )
    er.async_get(hass).async_get_or_create(
        "calendar",
        DOMAIN,
        f"{DOMAIN}_{DEVICE_ID}_schedule_calendar",
        config_entry=config_entry,
        device_id=readded.id,
        suggested_object_id="living_room_schedule",
        disabled_by=er.RegistryEntryDisabler.DEVICE,
    )

    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    entry = er.async_get(hass).async_get("calendar.living_room_schedule")
    assert entry.unique_id == f"{DOMAIN}_{SERIAL}_schedule_calendar"
    assert entry.disabled_by is None


async def test_only_heaters_gone_from_account_can_be_deleted(
    hass: HomeAssistant, mock_client: AsyncMock, config_entry
) -> None:
    """The UI's delete button works for stale heaters but not for live ones."""
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    dev_reg = dr.async_get(hass)
    live = dev_reg.async_get_device_by_identifier((DOMAIN, SERIAL), config_entry.entry_id)
    stale = dev_reg.async_get_or_create(
        config_entry_id=config_entry.entry_id, identifiers={(DOMAIN, "OTHER-SERIAL")}
    )

    assert not await async_remove_config_entry_device(hass, config_entry, live)
    assert await async_remove_config_entry_device(hass, config_entry, stale)


async def test_services_resolve_serial_keyed_entities(
    hass: HomeAssistant, mock_client: AsyncMock, config_entry
) -> None:
    """Services still reach the heater by its Envi id after re-keying on the serial."""
    from custom_components.smart_envi.services import _get_device_id_from_entity

    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    entity_id = er.async_get(hass).async_get_entity_id("climate", DOMAIN, f"{DOMAIN}_{SERIAL}")
    assert _get_device_id_from_entity(hass, entity_id) == DEVICE_ID


async def test_refresh_all_only_refreshes_real_entries(
    hass: HomeAssistant, mock_client: AsyncMock, config_entry, caplog
) -> None:
    """refresh_all refreshes each account without tripping over the coordinator key."""
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    mock_client.get_device_state.reset_mock()

    await hass.services.async_call(DOMAIN, "refresh_all", blocking=True)
    await hass.async_block_till_done()

    mock_client.get_device_state.assert_called_once_with(DEVICE_ID)
    assert "Failed to refresh heaters" not in caplog.text
