# Changelog

## 1.2.0 — BioTec-L: Boiler State, codes and missing sensors

From the controller manual "Technical instructions REGULATION BioTec-L" and the diagnostics of a BioTec-L (v2.47aL) in [#1](https://github.com/Internetrevizor/centrometal-cloud/issues/1).

- **New on a BioTec-L: Boiler State**, with the BioTec-L operation phases (pages 60–62): `OFF: Switched off`, `S1: Ignition 2/3, waiting for flue gas above 50 °C`, `GLW2: Keeping the glow` and the rest, listed in PARAMETERS.md. Until now the phase was a disabled, hidden sensor named "B_STATE"; that entry is enabled and becomes `sensor.<device>_boiler_state`. If you had enabled it yourself, it keeps its entity ID. Home Assistant reloads the integration once, about 30 seconds after the first start, as it does whenever an entity is enabled.
- **Every BioTec (`biotec`): -55 °C is unknown.** The portal sends -55 for a sensor the controller does not read, where the controller's own screen shows "-". The diagnostics showed it for the mixer and DHW temperatures.
- **BioTec-L codes are named after the manual** (pages 64–72): the disabled diagnostic sensors "W11" and "W12" are now "W11 Out of fuel" and "W12 Low buffer temperature", and the same for every E, W and I code. They stay disabled: what their value says has not been seen yet.
- PelTec II and every other family: nothing changes. No other entity, entity ID, name or state text changes.

## 1.1.0 — the boiler schedule as a calendar

- **New: Boiler Schedule calendar (PelTec II, read-only).** The controller's three weekly tables of boiler operating times and the "Boiler schedule" selector are read the way the portal reads them, `{"PRD 223": "VAL", "PRD 224": "ALV"}` and the same for 225 and 226, after setup and then every six hours. The calendar's events are the windows of the active table, in Home Assistant's time zone; with the selector on Off it has none. Its attributes give the active table and each table day by day ("04:00-08:00, 17:30-23:00"). The layout comes from the controller manual (pages 30–31) and was checked against a PelTec II Lambda read through the portal: ten values a day (T1–T5 starts and stops), minutes after midnight, bit 15 on a start, 1440 for an unused value.
- The schedule values (`PVAL` of slots 223–226) are now kept when they arrive; their defaults and limits are still dropped.
- **Settings are read with their limits.** A setting the portal leaves out is read the way the portal reads it when its settings page opens, one slot per request: `{"PRD 67 0": "ALL"}`, which brings the value, the minimum, the maximum and the default together. The earlier `{"PRD 67": "VAL"}` brought the value alone, so the setting could not be changed from Home Assistant until the limits arrived some other way, and the read was repeated every hour.
- No existing entity, entity ID, name or state text changes.

## 1.0.5 — entity names for Home Assistant 2026.10 and later

- Home Assistant 2026.10 puts the device name in front of the name of every entity that does not name itself after its device. Every entity carried the product in its own name and the device was "Centrometal Boiler <product> <power> <serial>", so a new install got names such as "Centrometal Boiler PelTec II Lambda 36 SN000001 PelTec II Lambda Boiler Temperature" and entity IDs to match. Every entity now names itself after its device (`has_entity_name`): the device is named after the product ("PelTec II Lambda", after the optional prefix and, with several boilers, the serial), and each entity keeps only its own part ("Boiler Temperature"). A new install gets the entity IDs it got before 2026.10 (`sensor.peltec_ii_lambda_boiler_temperature`).
- Existing installs keep their entity IDs, so automations keep working. The device name and the displayed entity names change to the form above.
- The option **Prefix entity names with the product name** is removed: Home Assistant 2026.10 and later ignored it, and renaming the device does the same.
- The connection sensor is named "System Connection" ("PelTec II Lambda System Connection").
- The Home Assistant tests run on both an older and a current Home Assistant release.

## 1.0.4 — PelTec Compact on/off, and no rejected values on numeric sensors

- **PelTec Compact:** the boiler on/off switch is created, as on the PelTec, whose controller the Compact shares. Its boiler command value was already left out of the sensors in favour of that switch, so neither existed. The hydraulic configuration shows the scheme name ("4. BUF") instead of its index, and the burner grate sensor is created when the boiler reports the grate.
- **Every family except PelTec II:** a sensor with a unit, a state class or a display precision reports "unknown" instead of a non-numeric value such as the "?" a parameter carries before the controller reports it. Home Assistant refused those values and logged an error at every update; counters were affected first.

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
