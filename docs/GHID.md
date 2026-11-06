# Centrometal Cloud integration guide (PelTec II Lambda)

Status on 06.11.2026, version **1.0.0**. Repository `Internetrevizor/centrometal-cloud`, domain `centrometal_cloud`. It replaces `Internetrevizor/hass-centrometal-boiler` (archived; same code, earlier domain `centrometal_boiler`), which itself began as a fork of `9a4gl/hass-centrometal-boiler` (Tihomir Heidelberg, Apache 2.0, credited in `README.md` and `NOTICE`). The companion project `Internetrevizor/centrometal-local-mqtt` (domain `centrometal_local`) runs the same boiler without the cloud.

This guide and `CLAUDE.md` are internal notes: they stay in the repository, but `.gitattributes` keeps them out of every release archive, and HACS installs only `custom_components/` anyway. The owner reads and writes in Romanian; replies to the owner are in Romanian, while everything in the repository is in English.

## 1. What it is

A Home Assistant integration (custom component, installed through HACS) for Centrometal boilers connected to the cloud portal (web-boiler.com) through a CM WiFi-Box or the controller's built-in WiFi. It reads data over HTTP (polling) and WebSocket (STOMP, realtime) and sends commands (boiler on/off, circuits, editable settings).

- Domain: `centrometal_cloud`
- Code: `custom_components/centrometal_cloud/`
- Supported families: PelTec II (`peltec2`), PelTec (`peltec`), Compact, CM Pelet-set, BioTec, BioTec Plus. The details below are for **PelTec II**.

## 2. The owner's installation

| | |
|---|---|
| Boiler | PelTec II Lambda, controller firmware `v3.03dL` |
| Hydraulic scheme | **43** (`B_KONF` = 42): "CAS" buffer (upper/lower sensors) + circuit **K1 = DHW** |
| P1 | the **DHW pump** of circuit K1, the same pump as `K1B_P` (entity "DHW Pump (K1)"). `B_P1` has no entity of its own: in a capture, `B_P1` and `K1B_P` switched in the same millisecond on all seven cycles. |
| P2 | the **DHW recirculation pump** (K1), entity "P2 DHW Recirculation Pump (K1)" |
| P3, P4 | not used in scheme 43 (attribute `Function: Not used in this configuration`) |
| 4-way mixing valve | on the boiler circuit, automatic (`B_misP`, "4-Way Mixing Valve Position") |
| DHW sensor | not installed (the portal shows "-°C") |

Source for scheme 43: boiler manual, page 57.

## 3. Installing and updating

1. HACS → Centrometal Cloud → ⋮ → **Update information** → install the new version (or manually, from the release archive).
2. Restart Home Assistant.
3. On start, registry entries of entities the integration does not create are removed. The cleanup is skipped when the portal data looks incomplete.

Entity IDs follow the `unique_id` (`<serial>-<parameter>`) and do not change between versions.

Moving from `hass-centrometal-boiler` (the owner chose a clean install, 06.11.2026): remove the old integration and its folder, restart, install this one and add it with the same account. Entity names are unchanged, so the entity IDs and their history carry over; areas and renames are set again. Check the seven settings (`number.technical_room_…`): their IDs may come out without the area prefix.

## 4. Boiler State (`B_STATE`)

The texts follow the "Operation stages" table in the controller manual (pages 96–97). Automations that compare the text need the exact strings. The `Raw stage code` attribute holds the bare code (`S4`, `D6`, …) and is the safer choice for automations.

| Code | Text in Home Assistant |
|---|---|
| OFF | OFF: Switched off |
| S0 | S0: Initial fan blowing, waiting for grate initial position |
| S1 | S1: Not in use |
| S2 | S2: Initial pellet filling |
| S3 | S3: Waiting for flame |
| S3-1 | S3-1: Extended ignition / flame verification |
| S3-2 | S3-2: Additional ignition fuel charge |
| S4 | S4: Electric heater working after flame appears |
| S5 | S5: Flame developing |
| SP1…SP5 | SP1: Stabilising 1 … SP5: Stabilising 5 (the manual has only SP1–SP3) |
| S6 | S6: Additional flame development |
| D0…D6 | D0: Power D0 (min) … D6: Power D6 (max) |
| S7 | S7: Shutdown stage |
| S7-1 | S7-1: Shutdown 1, waiting for flame to disappear |
| S7-2 | S7-2: Shutdown 2, fan at maximum speed |
| S7-3 | S7-3: Standby, waiting for start request |
| PF0 | PF0: Power failure — electric heater on, waiting for flame |
| PF1 | PF1: Power failure — flame appeared, electric heater off |
| PF2 | PF2: Power failure — flame developing |
| PF3 | PF3: Power failure — waiting for flame to disappear |
| PF4 | PF4: Power failure — final fan blowing |
| C0 | C0: Grate cleaning |

`tests/test_operation_stage_labels.py` pins the full list, so none of them can change by accident.

Other PelTec II decoding:
- `B_start` ("Burner Command"): 0 Stopped, 1 Running, 2 Stopping, 3 Cleaning. With `B_STATE` = S7-3 it shows "Paused / standby".
- `B_specG` ("Status Mark"): 0 None, 1 R (flame lost), 2 B (pellet tube bimetal), 3 T (turbulators), 4 G (grate cleaning), 5 F.

## 5. PelTec II hydraulic schemes

`B_KONF` is the scheme number minus one (the portal and the controller screen show the real number). The full table of the 45 schemes is in `custom_components/centrometal_cloud/peltec2.py` (`PELTEC2_SCHEMES`), transcribed from the boiler manual, chapter 4.2.2 (pages 23–58). It is cross-checked against the controller manual: the "DHW priority" list (page 52) and the "Installation" table (page 54).

What the scheme decides:

| Entity | Created in schemes |
|---|---|
| Buffer Tank Heat Request (`B_bup`) | 11–44 |
| DHW Priority (`B_PTV_PRI`) | 2, 5, 6, 9, 10, 13–20, 25, 32, 35, 40, 43, 44 |
| DHW Recirculation Enabled / Pump (`B_REC`, `B_REO`) | every scheme with a DHW recirculation pump |

What relay P1 drives, according to the manual:

| P1's role | Schemes |
|---|---|
| K1 circuit pump (radiators / underfloor) | 1–4, 6, 7, 21–27, 30–42 |
| DHW pump on K1 | 9, 10, 43, 44 |
| 3-way diverter valve; the boiler pump P(PWM) moves the water | 13–16 |
| Buffer tank pump | 17–20 |
| K2 circuit pump | 28, 29 |
| DHW recirculation pump | 8, 12 |
| Shared K1 / DHW pump; the 3-way valve is on P2 | 5 |
| Not used | 11, 45 |

Relays P1–P4 are named after their role in the active scheme (for example "P2 DHW Recirculation Pump (K1)") and carry a `Function` attribute. Where P1 is the K1 circuit's own pump, no separate P1 entity is created (`K1B_P` already reports it). Where K1/K2 loads the DHW tank with its own pump, the circuit pump is named "DHW Pump (K1)" / "DHW Pump (K2)". A scheme the manual does not list (`B_KONF` ≥ 45) keeps a separate P1 entity only when there is no K1 pump.

The **Configuration** entity shows the scheme (for example `43. BUF + K1 DHW`) with the attributes Buffer tank, DHW tank, DHW recirculation and P1…P4.

The other parameters (temperatures, counters, K1 circuit, editable settings) are described in `PARAMETERS.md`.

## 5b. Community features

Taken from the other forks of the original integration (see `NOTICE`):
- **BioTec-Plus:** "Tank Level" (`B_razina`) and "Fuel Level" (`B_razP`, %), unavailable until the controller first reports them. The **"Pellet Mode"** button sends `SCCMD = 1` (wood to pellets; there is no command back). Taken from AndroFlo; not tested here on a real boiler.
- **Option "Prefix entity names with the product name"** in *Configure*: on by default; off drops "PelTec II Lambda" from the front of the names. Entity IDs do not change.
- **Translations** of the setup screens: English, French, Romanian. Entity names stay in English.
- **Write rules for settings**, from `centrometal-local-mqtt` (owner's approval, 06.11.2026): a write is finished only when the controller reports the new value (15 s, else an error saying it may still apply); a value the controller already reports is not written again (a restored value does not count); at most 6 writes per setting in 10 minutes.

Forks reviewed (22.10.2026): 9a4gl (the original, no changes since 03.2026), AndroFlo (active, BioTec-Plus only, its own external library), grigoras-cristinel (the base of the first version), TheCarpetMerchant / mgcd-jed (Compact, prefix option), ULazdins (pellet percentage), ravloony (no changes of its own). Not taken: the wood-fire relight prediction (AndroFlo, beta), the controller clock and the schedule tables.

## 6. Reference manuals

Both are published by Centrometal (centrometal.hr → downloads), in English. They are not in the repository: the repository is public and the manuals are the manufacturer's material.

**"Technical instructions Controller PelTec II Lambda"** (file `PelTec-II-Lambda-12-48-regulation-ENG.pdf`, 100 pages):
- p. 52: DHW priority (the schemes with a DHW tank);
- p. 54: Installation (which schemes have a buffer and which circuits);
- pp. 55–58: Manual test (P(PWM), P1–P4, valves);
- pp. 81–86: errors and warnings (E12 safety pressure switch, E18 no flame in the ignition stage, E19, E23, E24, W2, I1–I19);
- pp. 96–97: Operation stages (the S0…C0 and PF0–PF4 table);
- pp. 97–98: the R, T, G and B marks.

**"Technical instructions PelTec II Lambda"** (file `PelTec-II-Lambda-12-48-boiler-ENG.pdf`, 96 pages):
- chapter 4.2.2, pp. 23–58: the 45 configurations, with the pump and sensor legends;
- p. 57: configuration 43 (the owner's installation).

## 7. Publishing a version

**Approved** changes go straight to `main`, without a pull request (owner's rule since 23.10.2026). A pull request only when the owner asks for one.

**Releases are automatic** (`.github/workflows/release.yml`):
1. A new version changes `custom_components/centrometal_cloud/manifest.json` (`version`), the badge in `README.md`, `tests/test_repository_layout.py` (the expected version) and adds a `## X.Y.Z — ...` section to `CHANGELOG.md`.
2. On a push to `main`, the workflow sees that `vX.Y.Z` does not exist yet, runs Validate, Hassfest and HACS, then creates the tag and the release with the notes from that CHANGELOG section. Without a CHANGELOG section there is no release.
3. A push to `main` without a version change creates nothing.
4. A version with a suffix (for example `1.2.0b1`) is published as a pre-release.
5. In Home Assistant: HACS → Update information → install → restart (or manually, from the release archive).

Claude sessions cannot create releases or tags themselves (GitHub refuses them for this session type); the workflow creates them with the repository's own token.

The repository started on 06.11.2026 with a single commit at 1.0.0, at the owner's request: the code, tests and documentation carry no history of earlier versions. That history stays in the archived `hass-centrometal-boiler`.

## 8. Development and tests

- The tests need Home Assistant installed. Without it, ten test modules cannot be imported and are silently skipped.
- Locally: Python 3.13 + `pip install homeassistant aiohttp pytest pytest-asyncio ruff "websockets>=13.1" "certifi>=2024.7.4" voluptuous`, then `ruff check .` and `pytest`.
- **Tests in a real Home Assistant** (`tests_ha/`): the integration runs in Home Assistant (pytest-homeassistant-custom-component) against a fake Centrometal cloud (`tests_ha/fake_centrometal.py`: website + STOMP broker; it can push realtime values and simulate an outage or an expired session). In a separate environment: `pip install -r tests_ha/requirements.txt`, then `pytest -c tests_ha/pytest.ini tests_ha`.
- CI (`.github/workflows/validate.yml`): the `python` job (Python 3.14, unit tests) and the `home-assistant` job (Python 3.13, `tests_ha/`).
- Fixtures: `tests/fixtures/peltec2_lambda_real_snapshot.json` and `..._http_snapshot.json` (both with `B_KONF` 12, i.e. scheme 13). Their origin is unclear: the owner does not recognise them, and the owner's installation is on scheme 43.

## 9. Open items

1. **`B_REO` ("DHW Recirculation Pump") versus P2**: on a PelTec II the recirculation pump is always wired to a P relay (the manual puts it on one of P1–P4 in every scheme that has one), so `B_REO` probably duplicates "P2 DHW Recirculation Pump (K1)". The owner leaned towards "only the `B_P` pumps, not `B_RE`". The change was drafted (drop `B_REO` from the PelTec II table; the older PelTec keeps it; `B_REC` stays) and then stopped: **not applied, to be discussed**.
2. Check on the real Home Assistant: the pump names, the Configuration entity, a full burn S0 → D → S7.
3. Check the automations against the stage texts (the table in section 4).
4. The fixtures with `B_KONF` 12, of unclear origin.
5. Inclusion in the HACS default list (section 10): to be submitted by the owner.
6. Ask GitHub Support to purge the old commits still reachable through pull requests #1–#3 of the archived `hass-centrometal-boiler` (section 11).
7. **Settings missing from the portal's snapshot.** The snapshot does not always carry the editable settings (owner's diagnostics: on 25.10.2026 only 576, 67, 68 and 70; on 04.11.2026 only 576), although parameter-list lists all seven; they come back when the settings page is opened on the portal website. The integration therefore asks the controller for every listed setting whose value or minimum is missing, with `POST /api/inst/control/advanced/{id}` `{"parameters": {"PRD <slot>": "VAL"}}`, after setup and at most hourly while one is missing; a slot that arrives later fills its entity in; the last known value is shown across restarts (`Restored: true`). Source of the request: the original library's first commit (ccc8f34, 2021, `{"PRD 222": "VAL"}` from the portal web app); `centrometal-local-mqtt` sends the same read to the module. The owner confirmed on 04.11.2026 that it works on the real boiler. A value without `PMIN`/`PMAX` is shown but cannot be written.

## 10. Inclusion in the HACS default list

The list is the `hacs/default` repository; the owner submits the request from their own account (the "owner" check requires the pull request author to own the repository).

- Requirements: public repository with a description and topics, issues enabled, the HACS action without `ignore`, Hassfest, a published release made after both passed. No separate PyPI library is required (that rule applies only to Home Assistant core integrations).
- The domain `centrometal_cloud` does not clash with `9a4gl/hass-centrometal-boiler` (`centrometal_boiler`), the only Centrometal integration in the list (checked 06.11.2026).

Steps:
1. Fork `https://github.com/hacs/default` and create a new branch from `master`.
2. In the `integration` file, add `"Internetrevizor/centrometal-cloud",` in alphabetical order (case-insensitive): between `"intelliThings-official/home-assistant-intellithings",` and `"InTheDaylight14/nginx-proxy-manager-switches",`.
3. Open a pull request to `hacs/default` with their template filled in (links to the release and to successful HACS and Hassfest runs), with "Allow edits by maintainers" on. Do not request reviews: the template says the pull request is closed if you do.

## 11. Personal data

Nothing that identifies the owner belongs in the repository: no e-mail addresses, serial numbers, portal installation ids, real locations, file names or credentials. Tests and fixtures use placeholders (`SN000001`, id `1001`, "Example City", `USR:PelTec II - Example`).

The history of `hass-centrometal-boiler` was rewritten on 24.10.2026 to remove personal data; this repository starts clean.

In the archived repository, GitHub keeps the old commits reachable through the pull-request pages (#1–#3) until GitHub Support removes them. For new commits the owner enables *Settings → Emails → Keep my email addresses private* and *Block command line pushes that expose my email*.
