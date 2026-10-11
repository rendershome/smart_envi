# Testing the Develop Branch in HACS

## Quick Setup

To test the `develop` branch in Home Assistant via HACS:

### Method 1: Change Branch in HACS UI (Easiest)

1. **Open Home Assistant**
2. **Go to HACS → Integrations**
3. **Find "Envi Smart Heater"**
4. **Click the three dots (⋮) menu**
5. **Select "Repository settings"** or **"Redownload"**
6. **Change Branch**: Look for a "Branch" field and change it from `main` to `develop`
7. **Click "Update"** or **"Redownload"**
8. **Restart Home Assistant**

### Method 2: Re-add Repository with Develop Branch

If Method 1 doesn't work:

1. **Remove existing integration** (if installed):
   - HACS → Integrations → Find "Envi Smart Heater"
   - Click ⋮ → "Remove"
   
2. **Add repository with develop branch**:
   - HACS → Integrations → ⋮ → Custom repositories
   - Click "+ ADD CUSTOM REPOSITORY"
   - **Repository**: `https://github.com/rendershome/smart_envi`
   - **Category**: Integration
   - **Branch**: `develop` (if there's a branch field)
   - Click "ADD"

3. **Install**:
   - Search for "Envi Smart Heater"
   - Click "Install"
   - Restart Home Assistant

### Method 3: Manual Installation (For Testing)

If HACS branch switching doesn't work:

```bash
# On your Home Assistant system
cd /config/custom_components/smart_envi
git fetch origin
git checkout develop
git pull origin develop
```

Then restart Home Assistant.

## Verifying You're on Develop Branch

After updating, check the version in `manifest.json`:
- **Main branch**: `"version": "2.0.0"`
- **Develop branch**: `"version": "2.0.0"` (same, but with latest fixes)

Or check the file structure:
- **Develop branch** should have: `custom_components/smart_envi/translations/en.json`
- **Main branch** does NOT have this file (it was removed)

## Switching Back to Main

When done testing:

1. **HACS → Integrations → Envi Smart Heater**
2. **Click ⋮ → Repository settings**
3. **Change Branch back to `main`**
4. **Update**
5. **Restart Home Assistant**

## Current Develop Branch Changes

The `develop` branch currently includes:
- ✅ Fixed help text display (moved to `translations/en.json`)
- ✅ Added translations support in manifest.json
- ✅ Development workflow documentation

## Troubleshooting

**Problem**: HACS doesn't show branch option
- **Solution**: Use Method 2 or Method 3 (manual installation)

**Problem**: Changes not appearing after update
- **Solution**: 
  1. Clear browser cache
  2. Hard refresh (Ctrl+F5)
  3. Restart Home Assistant
  4. Check logs for errors

**Problem**: Integration not updating
- **Solution**: 
  1. Remove integration from HACS
  2. Re-add with develop branch
  3. Reinstall

## Notes

- The `develop` branch may contain experimental/unstable code
- Always test in a non-production environment if possible
- The `main` branch remains stable at v2.0.0
- Changes in `develop` will be merged to `main` when ready for release

