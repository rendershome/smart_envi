"""Calendar showing each Smart Envi heater's weekly schedule."""
from __future__ import annotations

from datetime import datetime, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator import EnviDataUpdateCoordinator
from .schedule import ScheduleEvent, events_between


class EnviScheduleCalendar(CoordinatorEntity[EnviDataUpdateCoordinator], CalendarEntity):
    """A heater's schedule: each event is a setpoint held until the next one."""

    _attr_has_entity_name = True
    _attr_translation_key = "schedule"
    _attr_icon = "mdi:calendar-clock"

    def __init__(self, coordinator: EnviDataUpdateCoordinator, device_id: str) -> None:
        super().__init__(coordinator)
        self.device_id = str(device_id)
        self._attr_unique_id = f"{DOMAIN}_{device_id}_schedule_calendar"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, self.device_id)})

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.get_device_data(self.device_id) is not None

    @property
    def event(self) -> CalendarEvent | None:
        """The setpoint period in progress now, or the next one."""
        now = dt_util.now()
        upcoming = self._events(now, now + timedelta(days=8))
        return next((e for e in upcoming if e.end > now), None)

    @property
    def extra_state_attributes(self) -> dict:
        schedule = self.coordinator.get_device_schedule(self.device_id) or {}
        return {"schedule_id": schedule.get("id"), "schedule_name": schedule.get("name")}

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        return self._events(start_date, end_date)

    def _events(self, start: datetime, end: datetime) -> list[CalendarEvent]:
        schedule = self.coordinator.get_device_schedule(self.device_id)
        if not schedule:
            return []
        unit = schedule.get("temperature_unit") or (
            self.coordinator.get_device_data(self.device_id) or {}
        ).get("temperature_unit", "")
        return [
            self._to_calendar_event(e, schedule.get("name"), unit)
            for e in events_between(schedule, start, end, dt_util.get_default_time_zone())
        ]

    @staticmethod
    def _to_calendar_event(
        event: ScheduleEvent, schedule_name: str | None, unit: str
    ) -> CalendarEvent:
        temperature = f"{event.temperature:g}°{unit}".rstrip("°")
        return CalendarEvent(
            start=event.start,
            end=event.end,
            summary=f"{event.title} · {temperature}",
            description=f"Schedule: {schedule_name}" if schedule_name else None,
        )


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up a schedule calendar for each heater."""
    coordinator: EnviDataUpdateCoordinator | None = hass.data.get(DOMAIN, {}).get(
        f"{DOMAIN}_coordinator_{entry.entry_id}"
    )
    if coordinator is None:
        return
    async_add_entities(
        EnviScheduleCalendar(coordinator, device_id) for device_id in coordinator.device_ids
    )
