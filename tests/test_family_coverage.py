"""Families the owner cannot test: what their users reported in other Centrometal integrations.

* PelTec Compact ("compact") shares the PelTec controller: the boiler on/off switch, the scheme names and the burner
  grate are the same. Its B_CMD sensor was already left out in favour of a switch that was never created, so the
  boiler state and the on/off command were missing altogether.
* A numeric sensor (unit, state class or display precision) must never report a non-numeric value: Home Assistant
  refuses it and logs an error at every update. The portal lists some parameters with "?" before the controller has
  reported them.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from custom_components.centrometal_cloud import switch as switch_platform  # noqa: E402
from custom_components.centrometal_cloud.centrometal_web_boiler.WebBoilerDeviceCollection import (  # noqa: E402
    WebBoilerDevice,
)
from custom_components.centrometal_cloud.sensors.WebBoilerConfigurationSensor import (  # noqa: E402
    WebBoilerConfigurationSensor,
)
from custom_components.centrometal_cloud.sensors.WebBoilerGenericSensor import WebBoilerGenericSensor  # noqa: E402
from custom_components.centrometal_cloud.switches.WebBoilerPowerSwitch import WebBoilerPowerSwitch  # noqa: E402
from tests.test_real_portal_capture_audit import _by_parameter, _run_sensor_setup  # noqa: E402

SERIAL = "SN000001"


def _device(device_type: str, parameters: dict | None = None) -> WebBoilerDevice:
    device = WebBoilerDevice("user@example.com")
    device.update(
        {
            "id": 1001,
            "serial": SERIAL,
            "place": "Example City",
            "address": "",
            "type": device_type,
            "product": "PelTec Compact",
            "circuits": {},
            "__client": None,
            "__system": None,
            "__prefix": "",
            "__multi_device": False,
        }
    )
    for code, value in (parameters or {}).items():
        device.create_parameter(code, value)
    return device


def _switches(device: WebBoilerDevice) -> list:
    added: list = []
    entry = SimpleNamespace(runtime_data=SimpleNamespace(client=SimpleNamespace(data={SERIAL: device})))
    asyncio.run(switch_platform.async_setup_entry(None, entry, lambda entities, update=True: added.extend(entities)))
    return added


def test_the_compact_has_the_boiler_switch() -> None:
    switches = _switches(_device("compact", {"B_CMD": "1", "B_STATE": "D3"}))
    assert [type(s) for s in switches] == [WebBoilerPowerSwitch]


def test_a_family_without_a_switch_still_gets_none() -> None:
    assert _switches(_device("biotec", {"B_CMD": "1"})) == []


def test_the_compact_names_its_scheme_like_the_peltec() -> None:
    device = _device("compact", {"B_KONF": "3"})
    sensor = WebBoilerConfigurationSensor.create_entities(None, device)[0]
    assert sensor.native_value == "4. BUF"


def test_the_compact_has_the_burner_grate_when_it_reports_one() -> None:
    with_grate = _device("compact", {"B_resInd": "2", "B_resDir": "1", "B_resMax": "10"})
    without = _device("compact", {"B_Tk1": "60"})
    for device in (with_grate, without):
        device["__client"] = SimpleNamespace(has_fresh_data=lambda *a, **k: True, data={SERIAL: device})
    grate = [e for e in asyncio.run(_run_sensor_setup(with_grate)) if type(e).__name__ == "WebBoilerFireGridSensor"]
    assert len(grate) == 1
    assert not [e for e in asyncio.run(_run_sensor_setup(without)) if type(e).__name__ == "WebBoilerFireGridSensor"]


def test_a_counter_without_a_value_is_unknown_not_a_question_mark() -> None:
    for device_type in ("peltec", "compact", "cmpelet", "biotec", "biopl", "peltec2"):
        device = _device(device_type, {"CNT_0": "?"})
        counter = _by_parameter(WebBoilerGenericSensor.create_conf_entities(None, device))["CNT_0"]
        assert counter.native_value is None, device_type
        device.get_parameter("CNT_0")["value"] = "1234"
        assert counter.native_value == "1234", device_type


def test_a_text_sensor_keeps_its_text() -> None:
    device = _device("peltec", {"B_VER": "v3.03dL"})
    sensors = _by_parameter(WebBoilerGenericSensor.create_common_entities(None, device))
    assert sensors["B_VER"].native_value == "v3.03dL"
