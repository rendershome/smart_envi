# Release v2.1.0-dev - Development/Testing Version

## ⚠️ Pre-Release Warning

This is a **pre-release/development version** for testing purposes. Use at your own risk.

## 🎉 New Features

### Schedule Management UI
- ✅ **"Manage All Schedules"** menu option in options flow
- ✅ **List all schedules** from API with device names and status
- ✅ **View schedule details** with edit/delete options
- ✅ **Edit schedules** directly from the list (by schedule_id)
- ✅ **Delete schedules** with confirmation
- ✅ Shows enabled (✓) / disabled (✗) status for each schedule
- ✅ Maps device IDs to friendly entity names

### Enhanced Help Text
- ✅ **Inline help text** on form fields (descriptions appear below each field)
- ✅ Help text for Polling Interval and API Timeout fields
- ✅ Help text for Schedule Editor fields
- ✅ Help icon (?) still links to GitHub HELP.md for detailed examples

### Translations & UI Improvements
- ✅ Moved `strings.json` to proper location: `translations/en.json`
- ✅ Added translations support to `manifest.json`
- ✅ Documentation URL points to HELP.md for better help experience
- ✅ Added translations for new schedule management steps

## 📋 Schedule Management Flow

1. **Settings → Devices & Services → Smart Envi → Options**
2. **Select "Manage All Schedules"**
3. **Choose a schedule** from dropdown (shows name, device, and status)
4. **View details** and choose:
   - **Edit Schedule** - Opens edit form with current values
   - **Delete Schedule** - Removes schedule (with confirmation)

## 🔧 Technical Changes

- Added `async_step_list_schedules()` - Fetches and displays all schedules
- Added `async_step_view_schedule()` - Shows schedule details with actions
- Added `async_step_edit_schedule_from_list()` - Handles editing from schedule list
- Updated `async_step_edit_schedule()` to support schedule_id-based editing
- Enhanced error handling for schedule operations
- Coordinator refresh after schedule changes

## 🐛 Bug Fixes

- Fixed help text display for Home Assistant 2025.12
- Fixed schedule editing to work with both device_id and schedule_id
- Improved error messages for schedule operations

## 📝 Testing

After installing and restarting Home Assistant:

1. **Test Schedule Management**:
   - Go to Settings → Devices & Services → Smart Envi → Options
   - Select "Manage All Schedules"
   - Verify schedules appear with device names
   - Test editing a schedule
   - Test deleting a schedule

2. **Test Help Text**:
   - Go to Integration Settings or Schedule Editor
   - Verify inline help text appears below fields
   - Click ? icon to see GitHub HELP.md

## 📦 Installation

This is a pre-release version. In HACS:
1. Go to the integration
2. Click "Redownload"
3. Select version `v2.1.0-dev`
4. Restart Home Assistant

## ⚠️ Notes

- This version is for testing only
- Stable version remains v2.0.0 on `main` branch
- Changes will be merged to `main` when ready for production release
- All schedule changes refresh the coordinator automatically

## 🔄 What's Changed Since Last v2.1.0-dev

- Added complete schedule management UI
- Added inline help text descriptions to form fields
- Updated translations for new features
- Improved error handling and user feedback
