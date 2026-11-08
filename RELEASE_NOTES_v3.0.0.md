# Release v3.0.0

Changes since `v2.1.2`.

## ⚠️ Breaking changes

- **Home Assistant 2026.11 or later is now required.** This release uses the new climate temperature properties, which don't exist on older versions. If you're on an older version, stay on `v2.1.2` until you upgrade.
- **The heater's `temperature_unit` attribute is now set by Home Assistant.** It shows the unit the values are displayed in, such as `°C`. The heater's own setting has moved to a new attribute, `device_temperature_unit`, which shows `C` or `F`. If a template or card reads `temperature_unit` to find the heater's own setting, point it at `device_temperature_unit`.

## 🐛 Fixes

- **No more deprecation warnings for the heater on Home Assistant 2026.11.** The heater now uses `native_temperature_unit`, `native_current_temperature` and `native_target_temperature`. The old names stop working in Home Assistant 2027.11.
- **The temperature unit shown now matches the values.** The integration's attribute was overwriting Home Assistant's own `temperature_unit`, so a heater set to °F on a °C system reported `F` next to values already converted to °C.

No other action is needed after updating.
