"""BioTec-L: the Boiler State texts, the names of the codes and the -55 of a sensor the controller does not read.

Source: "Technical instructions REGULATION BioTec-L", operation phases on pages 60-62, codes on pages 64-72.
Home Assistant automations compare against the Boiler State texts, so this pins every one of them.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from custom_components.centrometal_cloud import biotec_l  # noqa: E402
from custom_components.centrometal_cloud.centrometal_web_boiler.WebBoilerDeviceCollection import (  # noqa: E402
    WebBoilerDevice,
)

EXPECTED_STAGES = {
    "OFF": "OFF: Switched off",
    "S0": "S0: Ignition 1/3, fan at maximum speed",
    "S1": "S1: Ignition 2/3, waiting for flue gas above 50 °C",
    "SP1": "SP1: Setting the primary and secondary air",
    "SP2": "SP2: Stabilisation",
    "SD4": "SD4: Setting the air for power D4",
    "D4": "D4: Power D4",
    "D3": "D3: Power D3",
    "D2": "D2: Power D2",
    "D1": "D1: Power D1",
    "DOP0": "DOP0: Upper door open",
    "DIF1": "DIF1: Turning off (set temperature, low firebox or high flue gas temperature)",
    "DIF2": "DIF2: Waiting for the boiler to cool by the differential",
    "DIF3": "DIF3: Blowout while waiting for the boiler to cool",
    "DIF4": "DIF4: Restarting, setting the primary and secondary air",
    "GLW1": "GLW1: Shutting down to keep the glow",
    "GLW2": "GLW2: Keeping the glow",
    "GLW3": "GLW3: Glow blowout",
    "GLW4": "GLW4: New filling, setting the primary and secondary air",
    "OFF1": "OFF1: Shutting down, then OFF",
    "PF-ON": "PF-ON: Power failure — air zeroed, restarting automatically",
}


def _device(product: str = "BioTec-L", device_type: str = "biotec") -> WebBoilerDevice:
    device = WebBoilerDevice("user@example.com")
    device.update({"id": 1001, "serial": "SN000001", "type": device_type, "product": product})
    return device


def test_the_stage_texts_are_pinned() -> None:
    assert biotec_l.STAGES == EXPECTED_STAGES


def test_a_phase_after_a_power_failure_carries_the_prefix() -> None:
    assert biotec_l.stage_text("PF-GLW2") == "PF-GLW2: Power failure — Keeping the glow"
    assert biotec_l.stage_details("PF-D3")["stage_group"] == "power_failure_recovery"
    assert biotec_l.stage_details("PF-D3")["power_level"] == 3


def test_an_unlisted_stage_is_reported_as_unknown() -> None:
    assert biotec_l.stage_text("S7") == "Unknown (S7)"
    assert biotec_l.stage_text("PF-XYZ") == "Unknown (PF-XYZ)"
    assert biotec_l.stage_details("S7")["stage_group"] == "unknown"


def test_the_stage_groups() -> None:
    groups = {code: biotec_l.stage_details(code)["stage_group"] for code in EXPECTED_STAGES}
    assert groups["OFF"] == "off"
    assert {groups[code] for code in ("S0", "S1", "SP1", "SP2", "SD4")} == {"ignition_startup"}
    assert {groups[code] for code in ("D1", "D2", "D3", "D4")} == {"modulation"}
    assert groups["DOP0"] == "door_open"
    assert {groups[code] for code in ("DIF1", "DIF2", "DIF3", "DIF4")} == {"differential"}
    assert {groups[code] for code in ("GLW1", "GLW2", "GLW3", "GLW4")} == {"glow"}
    assert groups["OFF1"] == "shutdown"
    assert biotec_l.stage_details("D4")["power_level"] == 4
    assert biotec_l.stage_details("D4")["description"] == "Power D4"


def test_the_codes_reported_on_a_biotec_l_are_named_after_the_manual() -> None:
    assert biotec_l.code_name("W11") == "W11 Out of fuel"
    assert biotec_l.code_name("W12") == "W12 Low buffer temperature"
    assert biotec_l.code_name("E1") == "E1 DHW sensor"
    assert biotec_l.code_name("B_Tk1") is None
    assert biotec_l.code_name("W13") is None


def test_only_a_biotec_l_gets_the_biotec_l_texts() -> None:
    assert biotec_l.is_biotec_l(_device())
    assert not biotec_l.is_biotec_l(_device(product="BioTec"))
    assert not biotec_l.is_biotec_l(_device(product="BioTec-Plus", device_type="biopl"))
    assert not biotec_l.is_biotec_l(_device(product="PelTec II Lambda", device_type="peltec2"))


@pytest.mark.parametrize(
    ("value", "expected"),
    [("-55", None), (-55, None), ("-45", None), ("-44.9", -44.9), ("13.7", 13.7), ("40", 40.0), ("?", None), (None, None)],
)
def test_minus_55_is_a_sensor_the_controller_does_not_read(value, expected) -> None:
    assert biotec_l.valid_temperature(value) == expected


# The entities


@pytest.fixture
def hass_available():
    pytest.importorskip("homeassistant")


class _Client:
    def has_fresh_data(self) -> bool:
        return True


def _sensor_device(**parameters) -> WebBoilerDevice:
    device = _device()
    device["__client"] = _Client()
    device["__system"] = None
    for name, value in parameters.items():
        device.create_parameter(name, value)
    return device


def test_the_boiler_state_uses_the_biotec_l_phases(hass_available) -> None:
    from custom_components.centrometal_cloud.sensors.WebBoilerOperationStateSensor import (
        WebBoilerOperationStateSensor,
    )

    device = _sensor_device(B_STATE="GLW2")
    [entity] = WebBoilerOperationStateSensor.create_entities(None, device)
    assert entity.native_value == "GLW2: Keeping the glow"
    assert entity.extra_state_attributes["Stage group"] == "glow"
    assert entity.unique_id == "SN000001-B_STATE"


def test_a_peltec_ii_keeps_its_own_stage_texts(hass_available) -> None:
    from custom_components.centrometal_cloud.sensors.WebBoilerOperationStateSensor import (
        WebBoilerOperationStateSensor,
    )

    device = _sensor_device(B_STATE="S1")
    device["type"] = "peltec2"
    device["product"] = "PelTec II Lambda"
    [entity] = WebBoilerOperationStateSensor.create_entities(None, device)
    assert entity.native_value == "S1: Not in use"


def test_a_temperature_of_minus_55_is_unknown(hass_available) -> None:
    from custom_components.centrometal_cloud.sensors.WebBoilerGenericSensor import WebBoilerGenericSensor

    device = _sensor_device(B_Tptv1="-55", B_Tpov1="-55", B_Tk1="13.7", B_Tva1="7")
    entities = {entity.unique_id: entity for entity in WebBoilerGenericSensor.create_conf_entities(None, device)}
    assert entities["SN000001-B_Tptv1"].native_value is None
    assert entities["SN000001-B_Tpov1"].native_value is None
    assert entities["SN000001-B_Tptv1"].available is True
    # A valid value is kept as the portal sent it.
    assert entities["SN000001-B_Tk1"].native_value == "13.7"
    assert entities["SN000001-B_Tva1"].native_value == "7"


def test_the_hidden_code_entities_carry_the_manual_text(hass_available) -> None:
    from custom_components.centrometal_cloud.sensors.WebBoilerGenericSensor import WebBoilerGenericSensor

    device = _sensor_device(W11="A", W12="A", B_Ths1="-55")
    entities = {entity.unique_id: entity for entity in WebBoilerGenericSensor.create_unknown_entities(None, device)}
    assert entities["SN000001-W11"]._description == "W11 Out of fuel"
    assert entities["SN000001-W12"]._description == "W12 Low buffer temperature"
    assert entities["SN000001-B_Ths1"]._description == "B_Ths1"
    assert entities["SN000001-W11"].entity_registry_enabled_default is False
