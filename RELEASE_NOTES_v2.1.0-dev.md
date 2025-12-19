# Release v2.1.0-dev - Development/Testing Version

## ⚠️ Pre-Release Warning

This is a **pre-release/development version** for testing purposes. Use at your own risk.

## 🎉 New Features

### Simplified Schedule Management
- ✅ **Single "Manage Schedules" menu option** (combined device and all schedules)
- ✅ **Choose between**:
  - Edit schedule for a specific device
  - View and manage all schedules from account
- ✅ **List all schedules** with device names and enabled/disabled status
- ✅ **View schedule details** with edit/delete options
- ✅ **Edit schedules** directly from the list (by schedule_id)
- ✅ **Delete schedules** with confirmation
- ✅ Shows enabled (✓) / disabled (✗) status for each schedule

### Enhanced Help Text with Spacing
- ✅ **Inline help text** on form fields with proper spacing
- ✅ **Visual separation** between form elements and help text (added `\n\n` at start)
- ✅ Help text for Polling Interval and API Timeout fields
- ✅ Help text for Schedule Editor fields
- ✅ Help icon (?) links to GitHub HELP.md for detailed examples

### Translations & UI Improvements
- ✅ Moved `strings.json` to proper location: `translations/en.json`
- ✅ Added translations support to `manifest.json`
- ✅ Documentation URL points to HELP.md for better help experience
- ✅ Updated translations for simplified schedule flow

## 📋 Schedule Management Flow

1. **Settings → Devices & Services → Smart Envi → Options**
2. **Select "Manage Schedules"**
3. **Choose type**:
   - **Edit Schedule for a Specific Device** - Select device, then edit
   - **View and Manage All Schedules** - See all schedules, select one to edit/delete
4. **Edit or delete** as needed

## 🔧 Technical Changes

- Combined `schedule` and `manage_schedules` menu options into single `schedules` option
- Added `async_step_schedule_options()` - Intermediate step to choose schedule type
- Added `async_step_list_schedules()` - Fetches and displays all schedules
- Added `async_step_view_schedule()` - Shows schedule details with actions
- Added `async_step_edit_schedule_from_list()` - Handles editing from schedule list
- Updated `async_step_edit_schedule()` to support schedule_id-based editing
- Added spacing (`\n\n`) to all form field descriptions for better visual separation
- Enhanced error handling for schedule operations
- Coordinator refresh after schedule changes

## 🐛 Bug Fixes

- Fixed help text display for Home Assistant 2025.12
- Fixed schedule editing to work with both device_id and schedule_id
- Improved error messages for schedule operations
- Added proper spacing to form field descriptions

## 📝 Testing

After installing and restarting Home Assistant:

1. **Test Simplified Schedule Management**:
   - Go to Settings → Devices & Services → Smart Envi → Options
   - Select "Manage Schedules"
   - Choose "Edit Schedule for a Specific Device" - verify device selection works
   - Choose "View and Manage All Schedules" - verify all schedules appear
   - Test editing and deleting schedules

2. **Test Help Text Spacing**:
   - Go to Integration Settings or Schedule Editor
   - Verify there's visual spacing between form fields and help text
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

- **Simplified menu**: Combined schedule options into single "Manage Schedules"
- **Added spacing**: Form field descriptions now have proper visual separation
- **Improved UX**: Clearer flow with intermediate step for schedule type selection
- **Better organization**: All schedule management in one place
