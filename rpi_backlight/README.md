# Raspberry Disaplay Backlight

This integration will integrate the Raspberry PI backlight as a physical light into Home Assistant.

### Installation

Copy this folder to `<config_dir>/custom_components/rpi_backlight/`.

Add the following entry in your `configuration.yaml`:

```yaml
light:
  - platform: rpi_backlight
```
