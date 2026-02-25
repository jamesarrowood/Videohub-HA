# Blackmagic Videohub Home Assistant Custom Integration

This repository contains a custom Home Assistant integration that exposes a Blackmagic Videohub router as selectable output routes.

## What it provides

- Home Assistant config flow (`Settings -> Devices & Services -> Add Integration`)
- One `select` entity per Videohub output
- Output routing via UI by choosing an input from the select dropdown
- Service `blackmagic_videohub.route_output` for automations/scripts

## Install (HACS)

1. Push this repository to GitHub.
2. In Home Assistant, open HACS.
3. Go to `Integrations` -> menu (three dots) -> `Custom repositories`.
4. Add your GitHub repo URL and choose category `Integration`.
5. Install `Blackmagic Videohub` from HACS.
6. Restart Home Assistant.
7. Add the integration in `Settings -> Devices & Services`.

## Install (Manual)

1. Copy `custom_components/blackmagic_videohub` into your Home Assistant config directory under `custom_components/`.
2. Restart Home Assistant.
3. Add the integration and enter the Videohub IP/hostname and port (default `9990`).

## Notes

- The integration uses the Videohub text protocol over TCP (default port `9990`).
- Output and input indexes in the service call are zero-based, matching the Videohub protocol.

## Example service call

```yaml
service: blackmagic_videohub.route_output
data:
  entry_id: YOUR_CONFIG_ENTRY_ID
  output: 0
  input: 3
```
