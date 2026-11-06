# Changelog

## 1.0.1 — integration category

- The manifest gives the integration's category, Climate → Thermostats & heating (`climate.thermostats_heating`), which Home Assistant now uses to group integrations. The HACS check had warned that it was missing. Nothing changes in Home Assistant.

## 1.0.0 — first release

Home Assistant integration for Centrometal boilers connected to the Centrometal web portal (web-boiler.com), domain `centrometal_cloud`.

- **Connection:** the portal's HTTP API with a periodic refresh, plus its realtime (STOMP over WebSocket) channel; entities stay available on HTTP alone while the realtime channel is down, with backed-off reconnects and session recovery.
- **PelTec II (tested on a PelTec II Lambda, v3.03dL, scheme 43):** entities from a strict allowlist checked against a portal capture and the two Centrometal manuals; Boiler State texts from the controller manual's operation-stage table; the 45 hydraulic schemes from the boiler manual, which decide the buffer and DHW entities and name the pump relays P1–P4 after what they drive; working counters; event history.
- **Settings** the account may edit are `number` entities, bounded by the controller's own limits and written with the portal's `PWR` command. Settings the portal leaves out are read from the controller with `PRD`, at startup and at most hourly while one is missing; the last known value is shown across restarts with `Restored: true`. A write is finished only when the controller reports the new value; a value the controller already reports is not written again; one setting accepts at most six writes in ten minutes.
- **Switches:** boiler on/off and heating circuits.
- **BioTec-Plus:** Tank Level, Fuel Level and a Pellet Mode button (wood to pellets).
- **Other families** (PelTec, Compact, CM Pelet-set, BioTec): the mappings of the original project, not tested by the maintainer.
- **Options:** product-name prefix on entity names, refresh and reconnect timing. Setup and options screens in English, French and Romanian.
- **Diagnostics** download with credentials and location redacted.

Replaces `Internetrevizor/hass-centrometal-boiler` (domain `centrometal_boiler`); see "Coming from hass-centrometal-boiler" in the README.
