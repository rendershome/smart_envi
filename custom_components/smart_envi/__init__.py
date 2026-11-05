"""Smart Envi integration.

⚠️ UNOFFICIAL INTEGRATION: This integration is not created, maintained, or endorsed
by EHEAT, Inc. or Envi. It uses the Envi API in an unofficial capacity.

Smart Envi heaters manufactured by EHEAT, Inc. (https://www.eheat.com/)
Originally created by @wlatic (https://github.com/wlatic)
Currently maintained by @rendershome (https://github.com/rendershome)
Enhanced with coordinator, sensors, and binary sensors.
"""
from __future__ import annotations

import logging

from datetime import timedelta

from aiohttp import ClientTimeout

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import EnviApiClient, EnviAuthenticationError
from .const import DOMAIN, SCAN_INTERVAL
from .coordinator import EnviDataUpdateCoordinator
from .services import async_setup_services, async_unload_services

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.CLIMATE,
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
    Platform.CALENDAR,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Smart Envi from a config entry."""
    session = async_get_clientsession(hass)
    
    # Get options with defaults
    options = entry.options or {}
    api_timeout = options.get("api_timeout", 15)
    
    client = EnviApiClient(session, entry.data["username"], entry.data["password"], api_timeout=api_timeout)

    try:
        await client.authenticate()
    except EnviAuthenticationError as err:
        raise ConfigEntryAuthFailed from err
    except Exception as err:
        raise ConfigEntryNotReady from err

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = client
    
    # Get scan interval from options or use default
    scan_interval_seconds = options.get("scan_interval", 30)
    scan_interval = timedelta(seconds=scan_interval_seconds)
    
    # Initialize coordinator with configurable scan interval
    coordinator = EnviDataUpdateCoordinator(hass, client, entry.entry_id, scan_interval)
    hass.data[DOMAIN][f"{DOMAIN}_coordinator_{entry.entry_id}"] = coordinator
    await coordinator.async_config_entry_first_refresh()
    _async_migrate_to_serial_keys(hass, entry, coordinator)

    # Set up options update listener
    entry.async_on_unload(entry.add_update_listener(async_update_options))
    
    # Set up services (only once)
    if DOMAIN not in hass.data or "services_setup" not in hass.data.get(DOMAIN, {}):
        await async_setup_services(hass)
        hass.data.setdefault(DOMAIN, {})["services_setup"] = True
    
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


def _async_migrate_to_serial_keys(
    hass: HomeAssistant, entry: ConfigEntry, coordinator: EnviDataUpdateCoordinator
) -> None:
    """Re-key each heater's devices and entities on its serial number.

    Entities used to be keyed on the Envi device id, which changes whenever a
    heater is re-added in the Envi app, so a heater could end up with several
    devices and entity sets. For each heater this keeps one device (the
    serial-keyed one if it exists, otherwise the oldest enabled one, which
    carries the area, history and any renames) with one entity per type,
    preferring that device's own entities, and removes the rest.
    Runs on every setup, so it also picks up anything created before the
    heater's serial was known.
    """
    ent_reg = er.async_get(hass)
    dev_reg = dr.async_get(hass)

    for device_id in coordinator.device_ids:
        serial = coordinator.device_key(device_id)
        if serial == device_id:
            continue

        # Every device registered for this heater, under any id it has had
        group = []
        for device in dr.async_entries_for_config_entry(dev_reg, entry.entry_id):
            keys = {value for domain, value in device.identifiers if domain == DOMAIN}
            if keys & {serial, device_id} or device.serial_number == serial:
                group.append((device, keys))
        if not group:
            continue
        old_keys = set().union(*(keys for _, keys in group)) - {serial}
        if not old_keys:
            continue

        keeper = next(
            (device for device, keys in group if serial in keys),
            min(
                (device for device, _ in group),
                key=lambda d: (d.disabled_by is not None, d.created_at),
            ),
        )

        # Group this heater's entities by type: the unique_id after the key
        by_type: dict[str, list[er.RegistryEntry]] = {}
        for entity in er.async_entries_for_config_entry(ent_reg, entry.entry_id):
            for key in old_keys | {serial}:
                prefix = f"{DOMAIN}_{key}"
                if entity.unique_id == prefix or entity.unique_id.startswith(f"{prefix}_"):
                    by_type.setdefault(entity.unique_id[len(prefix):], []).append(entity)
                    break

        for suffix, entities in by_type.items():
            new_unique_id = f"{DOMAIN}_{serial}{suffix}"
            kept = next(
                (e for e in entities if e.unique_id == new_unique_id),
                min(
                    entities,
                    key=lambda e: (e.device_id != keeper.id, e.disabled_by is not None, e.created_at),
                ),
            )
            for entity in entities:
                if entity is not kept:
                    ent_reg.async_remove(entity.entity_id)
            # Entities only hidden because their old device was disabled come back
            disabled_by = kept.disabled_by
            if disabled_by is er.RegistryEntryDisabler.DEVICE and keeper.disabled_by is None:
                disabled_by = None
            ent_reg.async_update_entity(
                kept.entity_id,
                new_unique_id=new_unique_id,
                device_id=keeper.id,
                disabled_by=disabled_by,
            )

        dev_reg.async_update_device(keeper.id, new_identifiers={(DOMAIN, serial)})
        for device, _ in group:
            if device.id != keeper.id:
                dev_reg.async_remove_device(device.id)
        _LOGGER.info(
            "Merged heater %s (Envi ids %s) into one device keyed on its serial",
            serial,
            ", ".join(sorted(old_keys)),
        )


async def async_remove_config_entry_device(
    hass: HomeAssistant, entry: ConfigEntry, device_entry: dr.DeviceEntry
) -> bool:
    """Allow deleting a heater that is no longer in the Envi account."""
    coordinator = hass.data.get(DOMAIN, {}).get(f"{DOMAIN}_coordinator_{entry.entry_id}")
    if coordinator is None:
        return True
    live = {coordinator.device_key(device_id) for device_id in coordinator.device_ids}
    return not any(
        domain == DOMAIN and value in live for domain, value in device_entry.identifiers
    )


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    # Update API client timeout if changed
    options = entry.options or {}
    api_timeout = options.get("api_timeout", 15)
    
    client = hass.data[DOMAIN].get(entry.entry_id)
    if client:
        client.timeout = ClientTimeout(total=api_timeout)
    
    # Update coordinator scan interval if changed
    scan_interval_seconds = options.get("scan_interval", 30)
    scan_interval = timedelta(seconds=scan_interval_seconds)
    
    coordinator_key = f"{DOMAIN}_coordinator_{entry.entry_id}"
    coordinator = hass.data[DOMAIN].get(coordinator_key)
    if coordinator:
        coordinator.update_interval = scan_interval
        _LOGGER.info("Updated scan interval to %s seconds for entry %s", scan_interval_seconds, entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        # Clean up coordinator
        coordinator_key = f"{DOMAIN}_coordinator_{entry.entry_id}"
        if coordinator_key in hass.data.get(DOMAIN, {}):
            hass.data[DOMAIN].pop(coordinator_key, None)
        # Clean up client
        hass.data[DOMAIN].pop(entry.entry_id, None)
        # If no more entries, unload services and remove domain
        if not hass.data[DOMAIN]:
            hass.data[DOMAIN].pop("services_setup", None)
            await async_unload_services(hass)
            hass.data.pop(DOMAIN, None)
    return unload_ok
