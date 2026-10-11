# Smart Envi Integration - Help & Configuration Guide

## Integration Options

### Polling Interval (Scan Interval)

**Default**: 30 seconds (recommended)

**Range**: 10-300 seconds

**Guidelines**:
- **Lower values** (10-20 seconds): More frequent updates but higher API usage
- **Recommended** (30 seconds): Good balance between responsiveness and API usage
- **Higher values** (60-300 seconds): Less API usage but slower response to changes
- **Minimum**: 10 seconds to avoid API rate limiting

**When to adjust**:
- Decrease if you need faster updates for automations
- Increase if you're experiencing API rate limiting issues
- Keep at default for most use cases

### API Timeout

**Default**: 15 seconds (recommended)

**Range**: 5-60 seconds

**Guidelines**:
- **Lower values** (5-10 seconds): Faster failure detection but may timeout on slow connections
- **Recommended** (15 seconds): Works well for most internet connections
- **Higher values** (30-60 seconds): Better for slow/unstable internet connections

**When to adjust**:
- Increase if you have slow internet or frequent timeout errors
- Decrease if you want faster failure detection
- Keep at default for most use cases

## Schedule Editor

### Enable Schedule

Turn the schedule on or off. When disabled, the schedule will not run and the heater will maintain its current setting.

### Schedule Name

Optional name for this schedule. Examples:
- "Weekday Schedule"
- "Weekend Schedule"
- "Morning Routine"

### Time Entries

Configure when the heater should automatically change temperature.

**Format**: `HH:MM:SS,temperature,enabled`

**Parameters**:
- **Time**: 24-hour format (e.g., `08:00:00` for 8 AM)
- **Temperature**: 50-86°F
- **Enabled**: `true` or `false` (whether this time slot is active)

**Multiple Entries**: Separate with `|` (pipe character)

**Examples**:

Single entry:
```
08:00:00,72,true
```

Two entries (morning and evening):
```
08:00:00,72,true|22:00:00,68,true
```

**Sample Schedules**:

**Morning/Evening**:
```
07:00:00,72,true|22:00:00,68,true
```

**Work Day** (away during day):
```
06:00:00,70,true|08:00:00,62,true|17:00:00,70,true|22:00:00,65,true
```

**Weekend** (sleep in):
```
08:00:00,70,true|23:00:00,68,true
```

**All Day Comfort**:
```
00:00:00,70,true
```

## Troubleshooting

### Common Issues

**"Authentication failed"**
- Check your Envi account credentials
- Ensure your account has active heaters
- Try re-authenticating via the integration settings

**"No devices found"**
- Verify you have Envi heaters in your account
- Check the Envi app to ensure heaters are online
- Restart the integration

**"Device unavailable"**
- Check your internet connection
- Verify the Envi API is accessible
- Check the Home Assistant logs for specific errors
- Check the "Online" binary sensor for connectivity status

### Debug Logging

Enable debug logging to see detailed information:

```yaml
logger:
  logs:
    custom_components.smart_envi: debug
```

## Additional Resources

- [Full Documentation](https://github.com/rendershome/smart_envi)
- [Report Issues](https://github.com/rendershome/smart_envi/issues)

