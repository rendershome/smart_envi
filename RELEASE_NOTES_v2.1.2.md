# Release v2.1.2

Changes since `v2.1.1`.

## 🐛 Fixes

- **`smart_envi.refresh_all` no longer logs an error on every run.** The service mistook one of the integration's internal entries for an account, then logged `Failed to refresh heaters` and counted a failure. Your heaters still refreshed, so nothing else changes.

No action is needed after updating.
