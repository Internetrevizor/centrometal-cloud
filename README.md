# Centrometal Cloud for Home Assistant

![Version](https://img.shields.io/badge/version-1.0.1-blue.svg)
![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.11%2B-blue.svg)
![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)

A Home Assistant integration for Centrometal boilers connected to the Centrometal web portal ([web-boiler.com](https://www.web-boiler.com)) through the CM WiFi-Box or the controller's built-in WiFi. It reads the boiler over the portal's HTTP API and realtime channel, and turns the boiler, its heating circuits and its settings on, off or to a new value.

To run a PelTec II Lambda without the cloud, see the companion project [Centrometal Local MQTT Protocol](https://github.com/Internetrevizor/centrometal-local-mqtt).

**Tested on:** PelTec II Lambda, firmware v3.03dL, hydraulic scheme 43 (buffer + K1 DHW).

## PelTec II

PelTec II entities are created from a strict allowlist verified against an authenticated portal HTTP and WebSocket capture. Raw, hidden, duplicated, or unverified controller fields are not created as Home Assistant entities.

Editable settings are written with the portal's own command, and Home Assistant refuses a value outside the range the controller reports for that setting. Each setting keeps the resolution the portal gives it: whole degrees for the boiler and buffer rows, tenths for the DHW rows. The portal does not always send every setting, so the integration asks the controller for any setting the portal left out, with the portal's own read command, at startup and then at most once an hour while one is still missing. Until the answer arrives a setting shows the last value Home Assistant saw before a restart, with a `Restored: true` attribute. A setting whose range has not been reported yet is shown but cannot be changed.

A change made from Home Assistant is finished only when the controller reports the new value (it waits up to 15 seconds). A value the controller already reports is not written again, and one setting accepts at most six changes in ten minutes, so an automation stuck in a loop cannot wear out the controller's memory.

The integration does not create or load schedule, weather, or notification entities. Schedule values received inside the main boiler status stream are discarded before they enter the device parameter cache. Weather groups from the parameter-list response are discarded. There is no option to enable either feature.

Exposed PelTec II data includes:

- Boiler power and operating state
- Portal-visible temperatures with invalid-value filtering
- Heating-circuit enabled state, pump demand, pump state, target temperatures, and measured temperatures
- Pump, fan, heater, flame, vacuum, fuel-level, lambda, and Wi-Fi states where the portal meaning is confirmed. Fan speed itself is not exposed: this controller does not publish it to the portal, and an entity for it could only show a frozen zero. A pump reported both by the boiler and by its heating circuit produces one entity, not two.
- Photocell resistance, 4-way mixing-valve position, feeder-screw activity, turbulator-cleaner activity, and burner-grate position
- The hydraulic configuration by its scheme number and contents, as in the boiler manual; the pump relays P1–P4 are named after what they drive in that scheme, and buffer and DHW entities exist only where the scheme has them
- Operation stage texts that follow the controller manual's stage table (see [PARAMETERS.md](PARAMETERS.md#boiler-state) for the exact strings)
- Descriptive attributes for temporary shutdown marks and operation-stage groups
- Working counters, including corrected total/active boiler runtime labels
- Portal temperature settings, editable from Home Assistant when the account may change them, bounded by the controller's own minimum and maximum; read-only rows keep a plain sensor. Plus the K1 circuit switch
- Controller configuration, product, software version, active file, and event history
- Cloud/WebSocket connectivity and the decoded external-start input

The Lambda Probe entity is created even when the controller omits the reading while the boiler is not firing. Any finite numeric value supplied by the controller, including idle values such as `25.5`, is displayed; a later live combustion value updates normally without reloading the integration. The Wi-Fi signal entity follows the controller display: nonzero values are shown in dB, while portal value `0` represents the unavailable `---dB` state and recovers automatically when RSSI is reported.

PelTec, Compact, CM Pelet-set, BioTec and BioTec Plus boilers use the mappings of the original project. The maintainer has no such boiler and has not tested them; reports from owners are welcome.

## BioTec-Plus

Besides the common mappings, a BioTec-Plus (also sold as Morvan GMX EASY) gets:

- **Tank Level** (`B_razina`: Empty / Reserve / Full) and **Fuel Level** (`B_razP`, %). The controller can report them only after setup; until it does, both entities are unavailable rather than showing a made-up value.
- A **Pellet Mode** button that switches the boiler from wood to pellets. There is no remote command back to wood.

Both come from the AndroFlo BioTec-Plus fork, where they were confirmed on a real boiler. They are not tested by the maintainer here.

## Installation

### HACS (recommended)

[![Open your Home Assistant instance and open this repository inside HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Internetrevizor&repository=centrometal-cloud&category=integration)

Or by hand:

1. In Home Assistant, open **HACS**, then the **⋮** menu (top right) → **Custom repositories**.
2. Repository: `https://github.com/Internetrevizor/centrometal-cloud`, type: **Integration** → **Add**.
3. Search for **Centrometal Cloud** and **Download** it.
4. Restart Home Assistant.
5. Open **Settings → Devices & services → Add integration** and select **Centrometal Cloud**.

### Manual installation

1. Download the latest release from the [releases page](https://github.com/Internetrevizor/centrometal-cloud/releases) (*Source code (zip)*).
2. Copy the `custom_components/centrometal_cloud` folder from the archive into `config/custom_components/`.
3. Restart Home Assistant.
4. Open **Settings → Devices & services → Add integration** and select **Centrometal Cloud**.

### Coming from hass-centrometal-boiler

This integration replaces [Internetrevizor/hass-centrometal-boiler](https://github.com/Internetrevizor/hass-centrometal-boiler). Entity names are the same, so the entity IDs and their history carry over if the old integration is removed first:

1. Remove the old integration (**Settings → Devices & services → Centrometal Boiler System → Delete**), then its `custom_components/centrometal_boiler` folder, and restart.
2. Install this one and add it with the same account.

Areas, renamed entities and other customisations made on the old entities have to be set again.

## Updating

- **HACS:** open **HACS**, select **Centrometal Cloud** and install the update (if it does not show yet, **⋮ → Update information**), then restart Home Assistant.
- **Manual:** replace the `config/custom_components/centrometal_cloud` folder with the one from the new release, then restart Home Assistant.

Read the [changelog](CHANGELOG.md) first: when a release changes a state text, automations comparing that text need the new one.

## Configuration

Configuration is through the Home Assistant UI. Enter the Centrometal account e-mail, password, and optional entity-name prefix.

The integration options (**Configure**) control:

- **Prefix entity names with the product name**: on by default ("PelTec II Lambda Boiler Temperature"); off gives "Boiler Temperature". Only the displayed names change; entity IDs stay the same.
- HTTP refresh and reconnect timing.

There are no schedule or weather switches. The setup and options screens are available in English, French and Romanian; entity names stay in English.

When the integration stops creating an entity, its registry entry is removed on the next start. The cleanup is skipped for any boiler whose parameter snapshot looks incomplete, so an outage on the Centrometal side cannot delete working entities.

## "Last updated"

The `Last updated` attribute is the time the reading itself last changed, not the time of the last poll. The portal re-reports every parameter on every poll with a fresh timestamp even when the value is identical, so using that would show the same number on every entity and say nothing.

## Diagnostics

The Home Assistant diagnostics download includes the current parsed boiler data with credentials and location fields redacted, plus the connection health used to decide entity availability (websocket state, age of the last realtime message, time since the last successful HTTP refresh).

## Debug logging

```yaml
logger:
  default: info
  logs:
    custom_components.centrometal_cloud: debug
```

## TLS

HTTPS and WebSocket certificate verification is always enabled and cannot be turned off.

Under Home Assistant the integration reuses core's own shared SSL context, which is built from `certifi` (or from `REQUESTS_CA_BUNDLE` when one is configured) once per process. Outside Home Assistant the client falls back to its own `certifi`-based context, and to the interpreter's default trust store if `certifi` is not installed.

## Credits

Based on [9a4gl/hass-centrometal-boiler](https://github.com/9a4gl/hass-centrometal-boiler) by Tihomir Heidelberg and contributors (Apache License 2.0), rewritten since: portal client, PelTec II decoding, hydraulic schemes, editable settings and the test suite. See [NOTICE](NOTICE).

Also from the community: the BioTec-Plus Pellet Mode button, tank level handling and the idea of testing against a fake Centrometal cloud from [AndroFlo/hass-centrometal-boiler](https://github.com/AndroFlo/hass-centrometal-boiler); the estimated pellet percentage from ULazdins; the product-name prefix option from TheCarpetMerchant and mgcd-jed.

## License

Apache License 2.0. This is an independent community project and is not affiliated with Centrometal d.o.o.
