# Release v2.1.0

Changes since `v2.1.0-dev`.

## ⚠️ Breaking changes

- **Schedules are view-only.** The Envi API has no working endpoint for saving or deleting schedules (`schedule/{id}` returns 404), so the schedule editor has been removed. Edit schedules in the Envi app.
- **The `smart_envi.set_schedule` service is removed.** Remove it from any automations or scripts that call it. `get_schedule` is still available.

## 🎉 New features

- **Re-authentication:** when Envi rejects the saved password, Home Assistant now shows a *Re-authenticate* prompt where you enter the new password. You no longer have to delete and re-add the integration.
- **Reconfigure:** change the account email or password at any time from the integration's ⋮ menu → *Reconfigure*.
- **Schedule calendar:** each heater gets a calendar entity showing its weekly schedule.
- **Next Schedule Change sensor:** a timestamp sensor for the heater's next scheduled setpoint.
- **Schedule viewer:** *Configure → View schedules* shows each schedule's days, times and temperatures, and which heaters use it.

## 🐛 Fixes

- Login failures now include Envi's own reason in the log (for example `HTTP 400, msgCode 5010: Incorrect login credentials`) instead of a generic "Authentication failed". Passwords are never logged.
- Heater entity IDs no longer repeat the device name (`climate.x_x`).
- °C heaters use their own unit and get whole-degree targets instead of fractional °F conversions.
- Heaters show as unavailable when Envi reports them offline, instead of showing stale values.
- Sensors and binary sensors show data right away instead of staying *unknown* until the next poll.

## 🔧 Other

- Added an MIT license.
- CI now runs the test suite (pytest), hassfest and HACS validation.
- Developer tools: `scripts/live_check.py` for testing against the real Envi API (reads credentials from a `.env` file) and `scripts/envi_capture.py`, a mitmproxy add-on for recording Envi app traffic.

## Upgrading

1. In HACS, update **Envi Smart Heater** to v2.1.0.
2. Restart Home Assistant.
3. If Smart Envi asks you to re-authenticate, enter your current Envi password.
