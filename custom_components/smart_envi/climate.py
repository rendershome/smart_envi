import logging
from typing import ClassVar

from homeassistant.components.climate import ClimateEntity, ClimateEntityFeature
from homeassistant.components.climate.const import HVACMode
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo

from .const import (
    DOMAIN,
    MAX_TEMPERATURE,
    MAX_TEMPERATURE_C,
    MIN_TEMPERATURE,
    MIN_TEMPERATURE_C,
)
from .api import EnviApiError, EnviDeviceError, EnviAuthenticationError
from .coordinator import EnviDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# Mode mapping
MODE_MAP = {
    1: "Heat",
    3: "Auto",
    # Add other modes as discovered
}


class EnviHeater(CoordinatorEntity, ClimateEntity):
    """Representation of a Smart Envi heater using centralized coordinator.
    
    This entity provides climate control functionality for Smart Envi heaters,
    including temperature control and on/off functionality. It uses the
    DataUpdateCoordinator pattern for efficient data updates.
    
    Attributes:
        _attr_hvac_modes: Available HVAC modes (OFF, HEAT)
        _attr_supported_features: Supported climate features

    Temperatures are reported in the heater's own unit (°C or °F, as set in
    the Envi app); Home Assistant converts them for display if needed.
    """

    _attr_has_entity_name = True
    # The heater is the device's main entity, so it takes the device name as-is
    # (climate.living_room rather than climate.living_room_living_room).
    _attr_name = None
    _attr_icon = "mdi:radiator"  # Default icon, will update based on state
    _attr_entity_registry_enabled_default = True
    _attr_hvac_modes: ClassVar[list[HVACMode]] = [HVACMode.OFF, HVACMode.HEAT]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )
    _attr_target_temperature_step = 1.0
    _enable_turn_on_off_backwards_compatibility = False
    
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._update_from_coordinator()
        self.async_write_ha_state()

    def __init__(self, coordinator: EnviDataUpdateCoordinator, device_id: str) -> None:
        """Initialize the Smart Envi heater entity.
        
        Args:
            coordinator: DataUpdateCoordinator instance for fetching device data
            device_id: Unique device identifier from Envi API
        """
        super().__init__(coordinator)
        self.coordinator = coordinator
        self.client = coordinator.client
        self.device_id = str(device_id)
        
        # Set defaults - will be updated by _update_from_coordinator
        self._device_name = f"Smart Envi {device_id}"
        self._attr_unique_id = f"{DOMAIN}_{device_id}"
        self._temperature_unit_api = "F"
        self._current_temperature = None
        self._target_temperature = None
        self._attr_hvac_mode = HVACMode.OFF
        self._serial_no = None
        self._firmware_version = None
        self._model_no = None
        
        # Update from coordinator data
        self._update_from_coordinator()

    def _update_from_coordinator(self) -> None:
        """Update entity state from coordinator data.
        
        This method is called when the coordinator receives new data. It updates
        all entity attributes including temperature, HVAC mode, and extra state
        attributes. Handles temperature unit conversion automatically.
        """
        data = self.coordinator.get_device_data(self.device_id)
        if not data:
            return
        
        # Get temperature unit from device
        temp_unit = data.get("temperature_unit", "F").upper()
        self._temperature_unit_api = temp_unit
        
        # Temperatures are in the heater's own unit (see temperature_unit)
        self._current_temperature = data.get("ambient_temperature")
        self._target_temperature = data.get("current_temperature")
        
        # Update HVAC mode
        self._attr_hvac_mode = HVACMode.HEAT if data.get("state") == 1 else HVACMode.OFF
        
        # Update icon based on state
        if self._attr_hvac_mode == HVACMode.HEAT:
            self._attr_icon = "mdi:radiator"
        else:
            self._attr_icon = "mdi:radiator-off"
        
        # Update device info
        self._firmware_version = data.get("firmware_version")
        self._model_no = data.get("model_no")
        self._serial_no = data.get("serial_no", self._serial_no)
        
        # Update device name if it changed
        if data.get("name"):
            self._device_name = data.get("name")
        
        # Update extra state attributes with additional device information
        self._update_extra_attributes(data)

    def _update_extra_attributes(self, data: dict) -> None:
        """Update extra state attributes with device information."""
        schedule = data.get("schedule", {})
        schedule_name = None
        schedule_temp = None
        if isinstance(schedule, dict):
            schedule_name = schedule.get("name") or schedule.get("title")
            schedule_temp = schedule.get("temperature")
        
        self._attr_extra_state_attributes = {
            "signal_strength": data.get("signal_strength"),
            "wifi_ssid": data.get("ssid"),
            "location": data.get("location_name") or data.get("relative_location_name"),
            "firmware_version": data.get("firmware_version"),
            "model": data.get("model_no"),
            "serial_number": data.get("serial_no"),
            "mode": MODE_MAP.get(data.get("current_mode"), f"Mode {data.get('current_mode')}"),
            "mode_number": data.get("current_mode"),
            "temperature_unit": data.get("temperature_unit", "F"),
            "schedule_active": data.get("is_schedule_active", False),
            "schedule_name": schedule_name,
            "schedule_temperature": schedule_temp,
            "freeze_protect": self._parse_inverted_bool(data.get("freeze_protect_setting"), default_on=True),
            "child_lock": self._parse_inverted_bool(data.get("child_lock_setting"), default_on=False),
            "hold": data.get("is_hold", False),
            "geofence_active": data.get("is_geofence_active", False),
            "last_update": data.get("device_status_res_at") or data.get("device_status_req_at"),
        }

    def _parse_inverted_bool(self, value, default_on: bool = True) -> bool:
        """Parse API boolean values with inverted semantics.
        
        API returns True when feature is OFF, False when ON.
        
        Args:
            value: API value (bool, int, str, or None)
            default_on: Default value if None or unexpected type
            
        Returns:
            Inverted boolean (True = feature ON, False = feature OFF)
        """
        if value is None:
            return default_on
        if isinstance(value, bool):
            return not value
        if isinstance(value, (int, str)):
            if value in (1, "true", "True", "1"):
                return False
            if value in (0, "false", "False", "0"):
                return True
        return not bool(value)

    @property
    def available(self) -> bool:
        """Return if entity is available.

        Unavailable when Envi reports the heater offline (device_status 0):
        the cloud then keeps serving the last values it heard, which can be
        days old.
        """
        data = self.coordinator.get_device_data(self.device_id)
        return (
            self.coordinator.last_update_success
            and data is not None
            and data.get("device_status", 1) != 0
        )

    @property
    def temperature_unit(self) -> str:
        """Return the heater's own temperature unit."""
        if self._temperature_unit_api == "C":
            return UnitOfTemperature.CELSIUS
        return UnitOfTemperature.FAHRENHEIT

    @property
    def min_temp(self) -> float:
        """Return the lowest target temperature the heater accepts."""
        return MIN_TEMPERATURE_C if self._temperature_unit_api == "C" else MIN_TEMPERATURE

    @property
    def max_temp(self) -> float:
        """Return the highest target temperature the heater accepts."""
        return MAX_TEMPERATURE_C if self._temperature_unit_api == "C" else MAX_TEMPERATURE

    @property
    def current_temperature(self) -> float | None:
        """Return current temperature."""
        return self._current_temperature

    @property
    def target_temperature(self) -> float | None:
        """Return target temperature."""
        return self._target_temperature

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        model = self._model_no or "Smart Envi"
        
        # Build device name with location if available
        device_name = self._device_name
        location = None
        data = self.coordinator.get_device_data(self.device_id)
        if data:
            location = data.get("location_name") or data.get("relative_location_name")
        if location and location not in device_name:
            device_name = f"{device_name} ({location})"
        
        return DeviceInfo(
            identifiers={(DOMAIN, str(self.device_id))},
            name=device_name,
            manufacturer="EHEAT",
            model=model,
            sw_version=self._firmware_version or "Unknown",
            serial_number=self._serial_no,
            configuration_url="https://www.eheat.com",
        )

    async def async_set_temperature(self, **kwargs) -> None:
        """Set new target temperature.
        
        Args:
            **kwargs: May contain ATTR_TEMPERATURE with the target temperature in
                the heater's unit (Home Assistant converts to it before calling)
            
        Raises:
            HomeAssistantError: If temperature is invalid or setting fails
        """
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            raise HomeAssistantError("Temperature value is required")
        
        # Validate temperature range
        if not isinstance(temperature, (int, float)):
            raise HomeAssistantError(f"Invalid temperature value: {temperature}")
        
        unit = self._temperature_unit_api
        if temperature < self.min_temp or temperature > self.max_temp:
            raise HomeAssistantError(
                f"Temperature must be between {self.min_temp}°{unit} and {self.max_temp}°{unit}. "
                f"Received: {temperature}°{unit}"
            )

        # The heater takes whole degrees; send an int when the value is one
        temp_to_send = int(temperature) if float(temperature).is_integer() else temperature

        try:
            await self.client.set_temperature(self.device_id, temp_to_send)
            self._target_temperature = temperature
            _LOGGER.debug("Set temperature to %s°%s for %s", temp_to_send, unit, self.device_id)
            # Refresh this device's data immediately
            await self.coordinator.async_refresh_device(self.device_id)
            self._update_from_coordinator()
        except EnviDeviceError as e:
            _LOGGER.exception("Device error setting temperature: %s", e)
            raise HomeAssistantError(f"Failed to set temperature: {e}") from e
        except EnviApiError as e:
            _LOGGER.exception("API error setting temperature: %s", e)
            raise HomeAssistantError(f"Failed to set temperature: {e}") from e
        except Exception as e:
            _LOGGER.exception("Unexpected error setting temperature: %s", e)
            raise HomeAssistantError(f"Failed to set temperature: {e!s}") from e

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set HVAC mode (on/off).
        
        Args:
            hvac_mode: HVAC mode to set (HVACMode.HEAT or HVACMode.OFF)
            
        Raises:
            HomeAssistantError: If setting the mode fails
        """
        try:
            if hvac_mode == HVACMode.HEAT:
                _LOGGER.debug("Turning on heater %s", self.device_id)
                await self.client.set_state(self.device_id, 1)
                self._attr_hvac_mode = hvac_mode
                _LOGGER.debug("Turned on heater %s", self.device_id)
            else:
                _LOGGER.debug("Turning off heater %s", self.device_id)
                await self.client.set_state(self.device_id, 0)
                self._attr_hvac_mode = hvac_mode
                _LOGGER.debug("Turned off heater %s", self.device_id)
            # Refresh this device's data immediately
            await self.coordinator.async_refresh_device(self.device_id)
            self._update_from_coordinator()
        except EnviDeviceError as e:
            _LOGGER.exception("Device error setting HVAC mode: %s", e)
            raise HomeAssistantError(f"Failed to set HVAC mode: {e}") from e
        except EnviApiError as e:
            _LOGGER.exception("API error setting HVAC mode: %s", e)
            raise HomeAssistantError(f"Failed to set HVAC mode: {e}") from e
        except Exception as e:
            _LOGGER.exception("Unexpected error setting HVAC mode: %s", e)
            raise HomeAssistantError(f"Failed to set HVAC mode: {e!s}") from e

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities
):
    """Set up all Envi heaters from a config entry."""
    # Get coordinator (should already be created in __init__.py)
    coordinator_key = f"{DOMAIN}_coordinator_{entry.entry_id}"
    coordinator = hass.data[DOMAIN].get(coordinator_key)
    if not coordinator:
        _LOGGER.error("Coordinator not found for entry %s", entry.entry_id)
        return
    
    # Get device IDs from coordinator
    device_ids = coordinator.device_ids
    if not device_ids:
        _LOGGER.warning("No devices found for entry %s", entry.entry_id)
        return

    _LOGGER.info("Found %s Smart Envi heaters: %s", len(device_ids), device_ids)
    
    # Create entities using coordinator
    heaters = [EnviHeater(coordinator, device_id) for device_id in device_ids]
    
    _LOGGER.info("Created %s heater entities", len(heaters))
    async_add_entities(heaters)
