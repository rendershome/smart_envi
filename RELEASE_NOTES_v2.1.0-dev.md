# Release v2.1.0-dev - Development/Testing Version

## ⚠️ Pre-Release Warning

This is a **pre-release/development version** for testing purposes. Use at your own risk.

## Changes in This Version

### Fixed Help Text Display for Home Assistant 2025.12
- ✅ Moved `strings.json` to proper location: `translations/en.json`
- ✅ Added translations support to `manifest.json`
- ✅ **Removed `documentation` field** from manifest.json to enable inline help
- ✅ Help text now displays inline in options flow instead of linking to GitHub

## Why This Change

In Home Assistant 2025.12, the help icon (?) in options flow links to the `documentation` URL in `manifest.json` when present, which overrides inline help text. By removing the `documentation` field, Home Assistant will use the `data_description` entries from `translations/en.json` to display inline help text.

## Testing

This version is on the `develop` branch and includes fixes for the help text display issue. After installing and restarting Home Assistant:

1. Go to Settings → Devices & Services → Smart Envi → Options
2. Click the ? icons next to fields
3. **Expected**: Inline help text should appear
4. **If still linking to GitHub**: Clear browser cache and restart HA

## Installation

This is a pre-release version. In HACS:
1. Go to the integration
2. Click "Redownload"
3. Select version `v2.1.0-dev`
4. Restart Home Assistant

## Notes

- This version is for testing only
- Stable version remains v2.0.0 on `main` branch
- Changes will be merged to `main` when ready for production release
- Issue tracker URL remains in manifest.json for bug reporting
