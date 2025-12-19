"""Config flow for Smart Envi."""
from __future__ import annotations

import logging
from datetime import timedelta

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import entity_registry
from homeassistant.exceptions import HomeAssistantError

from .api import EnviApiClient, EnviAuthenticationError
from .const import (
    DOMAIN,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_API_TIMEOUT,
    MIN_SCAN_INTERVAL,
    MAX_SCAN_INTERVAL,
    MIN_API_TIMEOUT,
    MAX_API_TIMEOUT,
    MIN_TEMPERATURE,
    MAX_TEMPERATURE,
)

_LOGGER = logging.getLogger(__name__)


class EnviHeaterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the config flow for Smart Envi."""

    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            username = user_input["username"]
            password = user_input["password"]

            await self.async_set_unique_id(username.lower())
            self._abort_if_unique_id_configured()

            session = async_get_clientsession(self.hass)
            client = EnviApiClient(session, username, password)

            try:
                await client.authenticate()
                return self.async_create_entry(
                    title=f"Smart Envi ({username})",
                    data=user_input,
                )
            except EnviAuthenticationError:
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Unexpected error during setup")
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("username"): str,
                    vol.Required("password"): str,
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> EnviHeaterOptionsFlowHandler:
        """Get the options flow for this handler."""
        return EnviHeaterOptionsFlowHandler()


class EnviHeaterOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Smart Envi."""

    def __init__(self) -> None:
        """Initialize options flow."""
        self._schedule_data: dict | None = None
        self._device_id: str | None = None
        self._entity_id: str | None = None
        self._schedule_id: int | None = None
        self._all_schedules: list[dict] = []

    async def async_step_init(self, user_input: dict | None = None) -> FlowResult:
        """Show menu to choose between integration options and schedule editing."""
        # Show menu - when user selects an option, HA calls the step with that key
        return self.async_show_menu(
            step_id="init",
            menu_options={
                "integration": "Integration Settings (Scan Interval, API Timeout)",
                "schedules": "Manage Schedules",
            },
        )
    
    async def async_step_integration(self, user_input: dict | None = None) -> FlowResult:
        """Handle integration menu selection - redirect to integration_options."""
        return await self.async_step_integration_options(user_input)
    
    async def async_step_schedules(self, user_input: dict | None = None) -> FlowResult:
        """Handle schedules menu selection - show options for device-specific or all schedules."""
        return await self.async_step_schedule_options(user_input)
    
    async def async_step_schedule_options(self, user_input: dict | None = None) -> FlowResult:
        """Show options for schedule management: device-specific or all schedules."""
        if user_input is not None:
            schedule_type = user_input.get("schedule_type")
            if schedule_type == "device":
                return await self.async_step_select_device(user_input)
            elif schedule_type == "all":
                return await self.async_step_list_schedules(user_input)
        
        return self.async_show_form(
            step_id="schedule_options",
            data_schema=vol.Schema({
                vol.Required(
                    "schedule_type",
                    description="\n\n\nChoose how you want to manage schedules:\n\n• Device Schedule: Edit schedule for a specific heater\n• All Schedules: View and manage all schedules from your account",
                ): vol.In({
                    "device": "Edit Schedule for a Specific Device",
                    "all": "View and Manage All Schedules",
                }),
            }),
        )

    async def async_step_integration_options(self, user_input: dict | None = None) -> FlowResult:
        """Manage integration options (scan interval, API timeout)."""
        _LOGGER.debug("Integration options step called, user_input: %s", user_input)
        errors: dict[str, str] = {}
        
        try:
            if user_input is not None:
                # Validate scan interval
                scan_interval = user_input.get("scan_interval", DEFAULT_SCAN_INTERVAL)
                try:
                    scan_interval = int(scan_interval)
                except (ValueError, TypeError):
                    errors["scan_interval"] = "Scan interval must be a number"
                
                if not errors.get("scan_interval"):
                    if scan_interval < MIN_SCAN_INTERVAL or scan_interval > MAX_SCAN_INTERVAL:
                        errors["scan_interval"] = f"Scan interval must be between {MIN_SCAN_INTERVAL} and {MAX_SCAN_INTERVAL} seconds"
                
                # Validate API timeout
                api_timeout = user_input.get("api_timeout", DEFAULT_API_TIMEOUT)
                try:
                    api_timeout = int(api_timeout)
                except (ValueError, TypeError):
                    errors["api_timeout"] = "API timeout must be a number"
                
                if not errors.get("api_timeout"):
                    if api_timeout < MIN_API_TIMEOUT or api_timeout > MAX_API_TIMEOUT:
                        errors["api_timeout"] = f"API timeout must be between {MIN_API_TIMEOUT} and {MAX_API_TIMEOUT} seconds"

                if not errors:
                    # Store options
                    return self.async_create_entry(
                        title="",
                        data={
                            "scan_interval": scan_interval,
                            "api_timeout": api_timeout,
                        },
                    )

            # Get current values from config entry
            options = self.config_entry.options or {}
            current_scan_interval = options.get("scan_interval", DEFAULT_SCAN_INTERVAL)
            current_api_timeout = options.get("api_timeout", DEFAULT_API_TIMEOUT)
            
            # Ensure values are integers
            try:
                current_scan_interval = int(current_scan_interval)
            except (ValueError, TypeError):
                current_scan_interval = DEFAULT_SCAN_INTERVAL
            
            try:
                current_api_timeout = int(current_api_timeout)
            except (ValueError, TypeError):
                current_api_timeout = DEFAULT_API_TIMEOUT

            return self.async_show_form(
                step_id="integration_options",
                data_schema=vol.Schema(
                    {
                        vol.Required(
                            "scan_interval",
                            default=current_scan_interval,
                            description="\n\n\nHow often to check for device updates.\n\nDefault: 30 seconds\nRange: 10-300 seconds\n\nLower = more frequent updates but higher API usage\nHigher = less API usage but slower response",
                        ): vol.All(
                            vol.Coerce(int),
                            vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
                        ),
                        vol.Required(
                            "api_timeout",
                            default=current_api_timeout,
                            description="\n\n\nMaximum time to wait for API responses.\n\nDefault: 15 seconds\nRange: 5-60 seconds\n\nIncrease for slow internet, decrease for faster failure detection",
                        ): vol.All(
                            vol.Coerce(int),
                            vol.Range(min=MIN_API_TIMEOUT, max=MAX_API_TIMEOUT),
                        ),
                    }
                ),
                errors=errors,
            )
        except Exception as err:
            _LOGGER.exception("Error in integration options flow: %s", err)
            errors["base"] = "unknown"
            return self.async_show_form(
                step_id="integration_options",
                data_schema=vol.Schema({
                    vol.Required(
                        "scan_interval",
                        default=DEFAULT_SCAN_INTERVAL,
                        description="\n\n\nHow often to check for device updates.\n\nDefault: 30 seconds\nRange: 10-300 seconds\n\nLower = more frequent updates but higher API usage\nHigher = less API usage but slower response",
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
                    ),
                    vol.Required(
                        "api_timeout",
                        default=DEFAULT_API_TIMEOUT,
                        description="\n\n\nMaximum time to wait for API responses.\n\nDefault: 15 seconds\nRange: 5-60 seconds\n\nIncrease for slow internet, decrease for faster failure detection",
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(min=MIN_API_TIMEOUT, max=MAX_API_TIMEOUT),
                    ),
                }),
                errors=errors,
            )

    async def async_step_select_device(self, user_input: dict | None = None) -> FlowResult:
        """Select device to edit schedule."""
        errors: dict[str, str] = {}
        
        if user_input is not None:
            entity_id = user_input.get("entity_id")
            if entity_id:
                self._entity_id = entity_id
                # Get device_id from entity
                registry = entity_registry.async_get(self.hass)
                if registry_entry := registry.async_get(entity_id):
                    unique_id = registry_entry.unique_id
                    if unique_id.startswith(f"{DOMAIN}_"):
                        self._device_id = unique_id.replace(f"{DOMAIN}_", "", 1)
                    else:
                        self._device_id = unique_id
                    
                    # Load current schedule
                    return await self.async_step_edit_schedule()
                else:
                    errors["base"] = "entity_not_found"
        
        # Get all Smart Envi climate entities
        registry = entity_registry.async_get(self.hass)
        climate_entities = []
        
        for entity_id, entry in registry.entities.items():
            if entry.domain == "climate" and entry.platform == DOMAIN:
                state = self.hass.states.get(entity_id)
                if state:
                    friendly_name = state.attributes.get("friendly_name", entity_id)
                    climate_entities.append((entity_id, friendly_name))
        
        if not climate_entities:
            return self.async_abort(reason="no_devices")
        
        # Create schema with entity options
        entity_options = {entity_id: name for entity_id, name in climate_entities}
        
        return self.async_show_form(
            step_id="select_device",
            data_schema=vol.Schema({
                vol.Required("entity_id"): vol.In(entity_options),
            }),
            errors=errors,
            description_placeholders={
                "device_count": str(len(climate_entities)),
            },
        )

    async def async_step_edit_schedule(self, user_input: dict | None = None) -> FlowResult:
        """Edit schedule for selected device."""
        errors: dict[str, str] = {}
        
        # Get API client from domain data
        domain_data = self.hass.data.get(DOMAIN, {})
        client = domain_data.get(self.config_entry.entry_id)
        
        if not client:
            errors["base"] = "api_client_unavailable"
            return self.async_show_form(
                step_id="edit_schedule",
                data_schema=vol.Schema({}),
                errors=errors,
            )
        
        # Get current schedule
        if self._schedule_data is None and self._device_id:
            try:
                # Get device state to find schedule info
                device_data = await client.get_device_state(self._device_id)
                schedule_info = device_data.get("schedule", {})
                
                schedule_id = None
                if isinstance(schedule_info, dict):
                    schedule_id = schedule_info.get("schedule_id") or schedule_info.get("id")
                
                # Build schedule data
                self._schedule_data = {
                    "device_id": self._device_id,
                    "schedule_id": schedule_id,
                    "enabled": schedule_info.get("enabled", False) if isinstance(schedule_info, dict) else False,
                    "name": schedule_info.get("name") or schedule_info.get("title") if isinstance(schedule_info, dict) else None,
                    "temperature": schedule_info.get("temperature") if isinstance(schedule_info, dict) else None,
                    "times": schedule_info.get("times", []) if isinstance(schedule_info, dict) else [],
                }
                
                # Try to get full schedule details if schedule_id exists
                if schedule_id:
                    try:
                        schedule_list = await client.get_schedule_list()
                        for schedule in schedule_list:
                            if isinstance(schedule, dict) and schedule.get("id") == schedule_id:
                                self._schedule_data.update({
                                    "enabled": schedule.get("enabled", self._schedule_data["enabled"]),
                                    "name": schedule.get("name") or self._schedule_data["name"],
                                    "temperature": schedule.get("temperature") or self._schedule_data["temperature"],
                                    "times": schedule.get("times", self._schedule_data["times"]),
                                })
                                break
                    except Exception as e:
                        _LOGGER.debug("Could not fetch full schedule details: %s", e)
            except Exception as e:
                _LOGGER.error("Failed to get schedule: %s", e, exc_info=True)
                errors["base"] = "failed_to_load_schedule"
                self._schedule_data = {}
        
        if user_input is not None:
            # Validate and save schedule
            try:
                schedule_data = {
                    "enabled": user_input.get("enabled", False),
                }
                
                # Get schedule name
                name = user_input.get("name", "").strip()
                if name:
                    schedule_data["name"] = name
                
                # Parse time entries from structured text input
                # Format: "HH:MM:SS,temp,enabled|HH:MM:SS,temp,enabled"
                times = []
                time_entries_str = user_input.get("time_entries", "").strip()
                
                if time_entries_str:
                    for entry_str in time_entries_str.split("|"):
                        entry_str = entry_str.strip()
                        if not entry_str:
                            continue
                        
                        parts = entry_str.split(",")
                        if len(parts) >= 2:
                            time_str = parts[0].strip()
                            try:
                                temp = float(parts[1].strip())
                                enabled = parts[2].strip().lower() == "true" if len(parts) > 2 else True
                            except (ValueError, IndexError) as e:
                                errors["time_entries"] = f"Invalid format in entry '{entry_str}'. Use: HH:MM:SS,temp,enabled"
                                continue
                            
                            # Validate time format
                            try:
                                time_parts = time_str.split(":")
                                if len(time_parts) == 2:
                                    time_str = f"{time_str}:00"
                                elif len(time_parts) != 3:
                                    raise ValueError("Invalid time format")
                                # Validate each part is numeric
                                for part in time_str.split(":"):
                                    int(part)
                            except (ValueError, TypeError):
                                errors["time_entries"] = f"Invalid time format: {time_str}. Use HH:MM:SS"
                                continue
                            
                            # Validate temperature
                            if temp < MIN_TEMPERATURE or temp > MAX_TEMPERATURE:
                                errors["time_entries"] = f"Temperature {temp} must be between {MIN_TEMPERATURE} and {MAX_TEMPERATURE}°F"
                                continue
                            
                            times.append({
                                "time": time_str,
                                "temperature": temp,
                                "enabled": enabled,
                            })
                
                if not errors:
                    schedule_data["times"] = times
                    
                    # Get schedule_id for update or use device_id for creation
                    schedule_id = self._schedule_id or (self._schedule_data.get("schedule_id") if self._schedule_data else None)
                    
                    if schedule_id:
                        # Update existing schedule
                        await client.update_schedule(schedule_id, schedule_data)
                    else:
                        # Create new schedule
                        if not self._device_id:
                            errors["base"] = "device_id_required_for_creation"
                        else:
                            schedule_data["device_id"] = self._device_id
                            await client.create_schedule(schedule_data)
                    
                    # Refresh device data
                    coordinator_key = f"{DOMAIN}_coordinator_{self.config_entry.entry_id}"
                    coordinator = domain_data.get(coordinator_key)
                    if coordinator and hasattr(coordinator, "async_refresh_device"):
                        if self._device_id in coordinator.device_ids:
                            await coordinator.async_refresh_device(self._device_id)
                    
                    return self.async_create_entry(
                        title="",
                        data=self.config_entry.options or {},
                    )
            except Exception as e:
                _LOGGER.exception("Error saving schedule: %s", e)
                errors["base"] = "failed_to_save_schedule"
        
        # Build current schedule data for form
        current_schedule = self._schedule_data or {}
        current_times = current_schedule.get("times", [])
        
        # Format time entries as string for text input
        # Format: "HH:MM:SS,temp,enabled|HH:MM:SS,temp,enabled"
        time_entries_str = ""
        if current_times:
            time_parts = []
            for entry in current_times:
                if isinstance(entry, dict):
                    time_str = entry.get("time", "")
                    temp = entry.get("temperature", "")
                    enabled = entry.get("enabled", True)
                    time_parts.append(f"{time_str},{temp},{enabled}")
            time_entries_str = "|".join(time_parts)
        
        # Get entity friendly name for display
        entity_name = self._entity_id or "Unknown"
        if self._entity_id:
            state = self.hass.states.get(self._entity_id)
            if state:
                entity_name = state.attributes.get("friendly_name", self._entity_id)
        
        return self.async_show_form(
            step_id="edit_schedule",
            data_schema=vol.Schema({
                vol.Required(
                    "enabled",
                    default=current_schedule.get("enabled", False),
                    description="\n\n\nTurn the schedule on or off.\n\nWhen disabled, the schedule will not run",
                ): bool,
                vol.Optional(
                    "name",
                    default=current_schedule.get("name", ""),
                    description="\n\n\nOptional name for this schedule.\n\nExamples: 'Weekday Schedule', 'Weekend Schedule'",
                ): str,
                vol.Optional(
                    "time_entries",
                    default=time_entries_str,
                    description="\n\n\nFormat: HH:MM:SS,temperature,enabled\n\nSeparate multiple entries with | (pipe)\nTemperature: 50-86°F\n\nExample: 08:00:00,72,true|18:00:00,68,true",
                ): str,
            }),
            errors=errors,
        )
    
    async def async_step_list_schedules(self, user_input: dict | None = None) -> FlowResult:
        """List all schedules from the API."""
        errors: dict[str, str] = {}
        
        # Get API client
        domain_data = self.hass.data.get(DOMAIN, {})
        client = domain_data.get(self.config_entry.entry_id)
        
        if not client:
            errors["base"] = "api_client_unavailable"
            return self.async_show_form(
                step_id="list_schedules",
                data_schema=vol.Schema({}),
                errors=errors,
            )
        
        # Fetch all schedules
        if not self._all_schedules:
            try:
                self._all_schedules = await client.get_schedule_list()
                _LOGGER.debug("Fetched %s schedules", len(self._all_schedules))
            except Exception as e:
                _LOGGER.error("Failed to fetch schedules: %s", e, exc_info=True)
                errors["base"] = "failed_to_load_schedules"
                self._all_schedules = []
        
        # If user selected a schedule, go to view/edit
        if user_input is not None:
            schedule_id_str = user_input.get("schedule_id")
            if schedule_id_str:
                try:
                    self._schedule_id = int(schedule_id_str)
                    return await self.async_step_view_schedule()
                except (ValueError, TypeError):
                    errors["schedule_id"] = "Invalid schedule selection"
        
        # Build schedule options for dropdown
        # Format: "Schedule Name (Device) - ID: 123"
        schedule_options = {}
        device_map = {}  # Map device_id to entity name
        
        # Get device names from entity registry
        registry = entity_registry.async_get(self.hass)
        for entity_id, entry in registry.entities.items():
            if entry.domain == "climate" and entry.platform == DOMAIN:
                unique_id = entry.unique_id
                if unique_id.startswith(f"{DOMAIN}_"):
                    device_id = unique_id.replace(f"{DOMAIN}_", "", 1)
                    state = self.hass.states.get(entity_id)
                    if state:
                        friendly_name = state.attributes.get("friendly_name", entity_id)
                        device_map[device_id] = friendly_name
        
        for schedule in self._all_schedules:
            if not isinstance(schedule, dict):
                continue
            schedule_id = schedule.get("id")
            schedule_name = schedule.get("name") or "Unnamed Schedule"
            device_id = schedule.get("device_id")
            device_name = device_map.get(str(device_id), f"Device {device_id}")
            enabled_status = "✓" if schedule.get("enabled") else "✗"
            
            if schedule_id:
                schedule_options[str(schedule_id)] = f"{enabled_status} {schedule_name} ({device_name})"
        
        if not schedule_options:
            return self.async_abort(reason="no_schedules")
        
        return self.async_show_form(
            step_id="list_schedules",
            data_schema=vol.Schema({
                vol.Required(
                    "schedule_id",
                    description="\n\n\nSelect a schedule to view or edit.\n\nSchedules show enabled (✓) or disabled (✗) status",
                ): vol.In(schedule_options),
            }),
            errors=errors,
        )
    
    async def async_step_view_schedule(self, user_input: dict | None = None) -> FlowResult:
        """View and edit a specific schedule."""
        errors: dict[str, str] = {}
        
        if not self._schedule_id:
            return self.async_abort(reason="no_schedule_selected")
        
        # Get API client
        domain_data = self.hass.data.get(DOMAIN, {})
        client = domain_data.get(self.config_entry.entry_id)
        
        if not client:
            errors["base"] = "api_client_unavailable"
            return self.async_show_form(
                step_id="view_schedule",
                data_schema=vol.Schema({}),
                errors=errors,
            )
        
        # Load schedule data if not already loaded
        if self._schedule_data is None:
            try:
                schedule = await client.get_schedule(self._schedule_id)
                self._schedule_data = {
                    "schedule_id": schedule.get("id"),
                    "device_id": schedule.get("device_id"),
                    "enabled": schedule.get("enabled", False),
                    "name": schedule.get("name") or "",
                    "temperature": schedule.get("temperature"),
                    "times": schedule.get("times", []),
                }
                self._device_id = str(schedule.get("device_id", ""))
            except Exception as e:
                _LOGGER.error("Failed to load schedule %s: %s", self._schedule_id, e, exc_info=True)
                errors["base"] = "failed_to_load_schedule"
                self._schedule_data = {}
        
        # Handle user input (save or delete)
        if user_input is not None:
            action = user_input.get("action")
            
            if action == "delete":
                # Delete schedule
                try:
                    await client.delete_schedule(self._schedule_id)
                    _LOGGER.info("Deleted schedule %s", self._schedule_id)
                    # Refresh coordinator
                    coordinator_key = f"{DOMAIN}_coordinator_{self.config_entry.entry_id}"
                    coordinator = domain_data.get(coordinator_key)
                    if coordinator:
                        await coordinator.async_refresh()
                    return self.async_create_entry(
                        title="",
                        data=self.config_entry.options or {},
                    )
                except Exception as e:
                    _LOGGER.error("Failed to delete schedule: %s", e, exc_info=True)
                    errors["base"] = "failed_to_delete_schedule"
            
            elif action == "edit":
                # Go to edit form
                return await self.async_step_edit_schedule_from_list()
        
        # Display schedule details
        current_schedule = self._schedule_data or {}
        current_times = current_schedule.get("times", [])
        
        # Format time entries for display
        time_entries_str = ""
        if current_times:
            time_parts = []
            for entry in current_times:
                if isinstance(entry, dict):
                    time_str = entry.get("time", "")
                    temp = entry.get("temperature", "")
                    enabled = entry.get("enabled", True)
                    time_parts.append(f"{time_str},{temp},{enabled}")
            time_entries_str = "|".join(time_parts)
        
        # Get device name
        device_name = "Unknown Device"
        if self._device_id:
            registry = entity_registry.async_get(self.hass)
            for entity_id, entry in registry.entities.items():
                if entry.domain == "climate" and entry.platform == DOMAIN:
                    unique_id = entry.unique_id
                    if unique_id.startswith(f"{DOMAIN}_"):
                        device_id = unique_id.replace(f"{DOMAIN}_", "", 1)
                        if device_id == self._device_id:
                            state = self.hass.states.get(entity_id)
                            if state:
                                device_name = state.attributes.get("friendly_name", entity_id)
                            break
        
        return self.async_show_form(
            step_id="view_schedule",
            data_schema=vol.Schema({
                vol.Required(
                    "action",
                    description=f"\n\n\nSchedule: {current_schedule.get('name', 'Unnamed')} for {device_name}\n\nChoose an action",
                ): vol.In({
                    "edit": "Edit Schedule",
                    "delete": "Delete Schedule",
                }),
            }),
            errors=errors,
            description_placeholders={
                "schedule_name": current_schedule.get("name", "Unnamed Schedule"),
                "device_name": device_name,
                "enabled": "Enabled" if current_schedule.get("enabled") else "Disabled",
                "time_count": str(len(current_times)),
            },
        )
    
    async def async_step_edit_schedule_from_list(self, user_input: dict | None = None) -> FlowResult:
        """Edit schedule from the schedule list (reuses edit_schedule logic)."""
        # Use the same edit logic as device-based editing
        # Just ensure we have the schedule_id set
        if self._schedule_id and not self._schedule_data:
            # Load schedule data
            domain_data = self.hass.data.get(DOMAIN, {})
            client = domain_data.get(self.config_entry.entry_id)
            if client:
                try:
                    schedule = await client.get_schedule(self._schedule_id)
                    self._schedule_data = {
                        "schedule_id": schedule.get("id"),
                        "device_id": schedule.get("device_id"),
                        "enabled": schedule.get("enabled", False),
                        "name": schedule.get("name") or "",
                        "temperature": schedule.get("temperature"),
                        "times": schedule.get("times", []),
                    }
                    self._device_id = str(schedule.get("device_id", ""))
                except Exception as e:
                    _LOGGER.error("Failed to load schedule: %s", e)
        
        # Reuse the existing edit_schedule method logic
        return await self.async_step_edit_schedule(user_input)
