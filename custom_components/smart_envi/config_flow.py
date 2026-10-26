"""Config flow for Smart Envi."""
from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import voluptuous as vol

from .api import EnviApiClient, EnviApiError, EnviAuthenticationError
from .const import (
    DEFAULT_API_TIMEOUT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_API_TIMEOUT,
    MAX_SCAN_INTERVAL,
    MIN_API_TIMEOUT,
    MIN_SCAN_INTERVAL,
)
from .schedule import WEEKDAYS

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

    async def _async_validate_login(self, username: str, password: str) -> str | None:
        """Try to log in; return an error key for the form, or None on success."""
        session = async_get_clientsession(self.hass)
        client = EnviApiClient(session, username, password)
        try:
            await client.authenticate()
        except EnviAuthenticationError as err:
            _LOGGER.warning("Envi login failed: %s", err)
            return "invalid_auth"
        except Exception:
            _LOGGER.exception("Unexpected error validating Envi login")
            return "cannot_connect"
        return None

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> FlowResult:
        """Start reauth when the stored credentials are rejected."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Ask for a new password for the existing account."""
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()
        username = entry.data["username"]

        if user_input is not None:
            password = user_input["password"]
            if not (error := await self._async_validate_login(username, password)):
                return self.async_update_reload_and_abort(
                    entry, data_updates={"password": password}
                )
            errors["base"] = error

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required("password"): str}),
            description_placeholders={"username": username},
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Change the username and/or password of an existing entry."""
        errors: dict[str, str] = {}
        entry = self._get_reconfigure_entry()

        if user_input is not None:
            username = user_input["username"]
            password = user_input["password"]

            await self.async_set_unique_id(username.lower())
            if username.lower() != entry.unique_id:
                # Switching accounts must not collide with another configured entry.
                self._abort_if_unique_id_configured()

            if not (error := await self._async_validate_login(username, password)):
                return self.async_update_reload_and_abort(
                    entry,
                    unique_id=username.lower(),
                    title=f"Smart Envi ({username})",
                    data_updates={"username": username, "password": password},
                )
            errors["base"] = error

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        "username",
                        default=(user_input or entry.data).get("username", ""),
                    ): str,
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
    """Handle options flow for Smart Envi.

    Schedules are view-only: the Envi API has no known endpoint for saving
    or deleting them (schedule/{id} returns 404), so they are edited in the
    Envi app.
    """

    def __init__(self) -> None:
        """Initialize options flow."""
        self._schedules: dict[str, dict] = {}
        self._schedule_id: str | None = None

    async def async_step_init(self, user_input: dict | None = None) -> FlowResult:
        """Show menu to choose between integration options and viewing schedules."""
        return self.async_show_menu(
            step_id="init",
            menu_options=["integration_options", "schedules"],
        )

    async def async_step_integration_options(self, user_input: dict | None = None) -> FlowResult:
        """Manage integration options (scan interval, API timeout)."""
        _LOGGER.debug("Integration options step called, user_input: %s", user_input)
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validation is handled by vol.Schema with vol.Coerce and vol.Range
            # If we reach here, input is valid
            return self.async_create_entry(
                title="",
                data={
                    "scan_interval": user_input["scan_interval"],
                    "api_timeout": user_input["api_timeout"],
                },
            )

        # Get current values from config entry
        options = self.config_entry.options or {}
        current_scan_interval = options.get("scan_interval", DEFAULT_SCAN_INTERVAL)
        current_api_timeout = options.get("api_timeout", DEFAULT_API_TIMEOUT)

        # Ensure values are integers for defaults
        try:
            current_scan_interval = int(current_scan_interval)
        except (ValueError, TypeError):
            current_scan_interval = DEFAULT_SCAN_INTERVAL

        try:
            current_api_timeout = int(current_api_timeout)
        except (ValueError, TypeError):
            current_api_timeout = DEFAULT_API_TIMEOUT

        # Build schema once
        data_schema = vol.Schema({
            vol.Required(
                "scan_interval",
                default=current_scan_interval,
                description=" \n\nHow often to check for device updates. Default: 30 seconds. Range: 10-300 seconds. Lower values = more frequent updates but higher API usage. Higher values = less API usage but slower response.",
            ): vol.All(
                vol.Coerce(int),
                vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
            ),
            vol.Required(
                "api_timeout",
                default=current_api_timeout,
                description=" \n\nMaximum time to wait for API responses. Default: 15 seconds. Range: 5-60 seconds. Increase for slow internet, decrease for faster failure detection.",
            ): vol.All(
                vol.Coerce(int),
                vol.Range(min=MIN_API_TIMEOUT, max=MAX_API_TIMEOUT),
            ),
        })

        return self.async_show_form(
            step_id="integration_options",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_schedules(self, user_input: dict | None = None) -> FlowResult:
        """Pick a schedule to view."""
        if user_input is not None:
            self._schedule_id = user_input["schedule_id"]
            return await self.async_step_view_schedule()

        client: EnviApiClient | None = self.hass.data.get(DOMAIN, {}).get(self.config_entry.entry_id)
        if client is None:
            return self.async_abort(reason="api_client_unavailable")
        try:
            schedules = await client.get_schedule_list()
        except EnviApiError as err:
            _LOGGER.error("Failed to load schedules: %s", err)
            return self.async_abort(reason="failed_to_load_schedules")

        self._schedules = {
            str(s["id"]): s for s in schedules if isinstance(s, dict) and s.get("id") is not None
        }
        if not self._schedules:
            return self.async_abort(reason="no_schedules")

        heaters = self._heaters_by_schedule()
        options = {
            schedule_id: f"{s.get('name') or 'Unnamed'} ({', '.join(heaters.get(schedule_id, [])) or 'no heaters'})"
            for schedule_id, s in self._schedules.items()
        }
        return self.async_show_form(
            step_id="schedules",
            data_schema=vol.Schema({vol.Required("schedule_id"): vol.In(options)}),
        )

    async def async_step_view_schedule(self, user_input: dict | None = None) -> FlowResult:
        """Show one schedule. Submitting closes the dialog without changing anything."""
        if user_input is not None:
            return self.async_abort(reason="schedule_viewed")

        schedule = self._schedules.get(self._schedule_id or "")
        if schedule is None:
            return self.async_abort(reason="no_schedules")
        heaters = self._heaters_by_schedule().get(self._schedule_id, [])
        return self.async_show_form(
            step_id="view_schedule",
            data_schema=vol.Schema({}),
            description_placeholders={
                "schedule_name": schedule.get("name") or "Unnamed",
                "heaters": ", ".join(heaters) or "none",
                "schedule": format_schedule(schedule),
            },
        )

    def _heaters_by_schedule(self) -> dict[str, list[str]]:
        """Map schedule id -> names of the heaters that use it."""
        coordinator = self.hass.data.get(DOMAIN, {}).get(f"{DOMAIN}_coordinator_{self.config_entry.entry_id}")
        result: dict[str, list[str]] = {}
        for device_id, data in (getattr(coordinator, "device_data", None) or {}).items():
            schedule = data.get("schedule")
            if isinstance(schedule, dict) and schedule.get("schedule_id") is not None:
                result.setdefault(str(schedule["schedule_id"]), []).append(data.get("name") or device_id)
        return result


def format_schedule(schedule: dict) -> str:
    """Render a schedule's day groups and events as Markdown."""
    unit = schedule.get("temperature_unit") or ""
    lines: list[str] = []
    for group in schedule.get("schedule_data") or []:
        if not isinstance(group, dict):
            continue
        days = [day[:3].title() for day in WEEKDAYS if group.get(day)]
        if not days:
            continue
        lines.append(f"**{', '.join(days)}**")
        events = sorted(
            (e for e in group.get("events") or [] if isinstance(e, dict)),
            key=lambda e: str(e.get("local_time", "")),
        )
        for event in events:
            temperature = event.get("heat_to")
            if temperature is None:
                temperature = event.get("temperature")
            if isinstance(temperature, (int, float)):
                temperature = f"{temperature:g}°{unit}"
            title = event.get("title") or "Scheduled change"
            lines.append(f"- {event.get('local_time', '?')}  {title}: {temperature}")
        lines.append("")
    return "\n".join(lines).strip() or "This schedule has no events."
