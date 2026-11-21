# Changelog

## 1.0.3 — realtime data again after a change on the Centrometal servers

- On 14.11.2026 Centrometal changed its realtime server: it refuses the subscription to `/topic/cm.inst.<type>.<serial>` (`ACCESS_REFUSED - read access to exchange 'amq.topic'`) for every account, so realtime updates stopped and values came only from HTTP polling. The integration now subscribes to `/exchange/stomp/cm.inst.<type>.<serial>`, and reads realtime messages with either destination.
- An installation listed by the portal without `product`, `place` or `address` no longer stops the setup with `KeyError: 'product'`; its entities are named "Centrometal ...".

## 1.0.2 — no reconnect loop when the portal refuses the realtime subscription

Fixes [#1](https://github.com/Internetrevizor/centrometal-cloud/issues/1). For some accounts the portal accepts the realtime (STOMP) login, then refuses the subscription to the boiler with `ACCESS_REFUSED - read access to exchange 'amq.topic'` and closes the connection. The reconnect loop started the next connection at once, about twice a second: each one logged an error (67,182 in nine hours in the report) and wrote the state of every entity twice. Values kept arriving by HTTP polling.

- A refused subscription is logged once, as a warning that values keep arriving by HTTP polling, and tried again once an hour. No relogin is started for it.
- Any realtime connection that ends before carrying data, or with an ERROR frame from the portal, is followed by a pause before the next one: 5 seconds, doubling up to 5 minutes. A connection that carries data resets the pause.
- Repeated realtime errors are one warning; the repeats are logged at debug level until data arrives again.

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
