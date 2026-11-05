# Release v2.1.1

Changes since `v2.1.0`.

## 🐛 Fixes

- **No more duplicate heaters after re-adding one in the Envi app.** Envi gives a heater a new device id every time it is re-added, and the integration used that id as the key for the heater's device and entities. Each re-add left the old device behind as "unavailable" and created a second set of entities (`climate.x_2`, `sensor.x_signal_strength_2`, …). Heaters are now keyed on their serial number, which never changes.
- **Existing duplicates are merged automatically.** On the first start after updating, every device a heater has had is combined into one:
  - The oldest enabled device is kept, with its area, history and any entity renames.
  - Entities that only existed on a newer copy (such as the schedule calendar) move over, and are re-enabled if they were only hidden because that copy was disabled.
  - The leftover duplicate devices and entities are removed.
- **Heaters removed from your Envi account can now be deleted** from the device page (⋮ → *Delete*). Heaters that are still in the account can't be deleted.

## ⚠️ Before updating

The merge removes duplicate entries from Home Assistant's device and entity registries. **Take a backup first.** If an automation, script or dashboard uses an entity from a newer duplicate (for example `climate.bedroom_basement` rather than `climate.bedroom_basement_bedroom`), point it at the kept entity after updating, or rename the kept entity to the ID you use.
