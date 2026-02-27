# Blackmagic Videohub Home Assistant Custom Integration

This repository contains a custom Home Assistant integration that exposes a Blackmagic Videohub router as selectable output routes.

## What it provides

- Home Assistant config flow (`Settings -> Devices & Services -> Add Integration`)
- One `select` entity per Videohub output
- One `media_player` entity per Videohub output (for built-in media player cards/source selection)
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
- Set scan interval to `0` in options to disable periodic polling (lowest network traffic).
- This repo also includes an optional Lovelace custom card in `lovelace/blackmagic-videohub-card.js` (manual copy to `/config/www`).

## Example service call

```yaml
service: blackmagic_videohub.route_output
data:
  entry_id: YOUR_CONFIG_ENTRY_ID
  output: 0
  input: 3
```

## Built-in Media Player Card (now supported)

The integration also creates `media_player` entities (one per Videohub output), so you can use Home Assistant's built-in media player card and switch routes using the source dropdown.

```yaml
type: media-control
entity: media_player.output_0_program
```

Tip: check the exact entity IDs under `Settings -> Devices & Services -> Blackmagic Videohub -> Entities`.

## Optional Lovelace Card (same repo)

This repo includes a simple custom card that makes routing easier than a plain entities card.

### Install the card

1. Copy `lovelace/blackmagic-videohub-card.js` to Home Assistant:

   - Destination: `/config/www/blackmagic-videohub-card.js`

2. Add the Lovelace resource:

   - `Settings -> Dashboards -> Resources -> Add Resource`
   - URL: `/local/blackmagic-videohub-card.js`
   - Type: `JavaScript Module`

3. Add a manual card with one of the YAML examples below.

### Auto-discovery example (easy mode)

This looks for `select` entities with `videohub` in the entity id.

```yaml
type: custom:blackmagic-videohub-card
title: Videohub Routing
```

### Explicit entities example (recommended if names are messy)

```yaml
type: custom:blackmagic-videohub-card
title: Videohub Routing
entities:
  - entity: select.blackmagic_videohub_output_0_program
    name: Program
  - entity: select.blackmagic_videohub_output_1_stream
    name: Stream
  - entity: select.blackmagic_videohub_output_2_recorder
    name: Recorder
```

### Presets example

```yaml
type: custom:blackmagic-videohub-card
title: Videohub Routing
presets:
  - name: Program -> Cam 1
    entry_id: YOUR_ENTRY_ID
    output: 0
    input: 0
  - name: Program -> Playback
    entry_id: YOUR_ENTRY_ID
    output: 0
    input: 5
```
