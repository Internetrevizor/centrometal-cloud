"""Cm Pelet-set: the configuration marking, the Boiler State texts, the names of the codes, -55.

Source: "Technical instructions CONTROLLER - CPREG-Touch", configuration on pages 50-51, burner working stages on
page 49, codes on pages 95-105. Home Assistant automations compare against the Boiler State texts, so this pins
every one of them.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from custom_components.centrometal_cloud import pelet_set  # noqa: E402
from custom_components.centrometal_cloud.centrometal_web_boiler.WebBoilerDeviceCollection import (  # noqa: E402
    WebBoilerDevice,
)

EXPECTED_STAGES = {
    "OFF": "OFF: Burner off",
    "A0": "A0: Burner start, fan only",
    "A1": "A1: Igniter on, start-up safety time running",
    "A2": "A2: Initial pellet filling",
    "A3": "A3: Waiting for flame",
    "A4": "A4: Flame, igniter still on",
    "A5": "A5: Igniter off, waiting for transition",
    "PP1": "PP1: Transition stage 1",
    "PP2": "PP2: Transition stage 2",
    "PP3": "PP3: Transition stage 3",
    "PP4": "PP4: Transition stage 4",
    "PP5": "PP5: Transition stage 5",
    "A6": "A6: Before nominal power",
    "P": "P: Nominal power",
    "P2": "P2: Nominal power P2",
    "P3": "P3: Nominal power P3",
    "P4": "P4: Nominal power P4",
    "P5": "P5: Nominal power P5",
    "P6": "P6: Nominal power P6",
    "M4": "M4: Modulation stage 4",
    "M3": "M3: Modulation stage 3",
    "M2": "M2: Modulation stage 2",
    "M1": "M1: Modulation stage 1",
    "PFON230": "PFON230: Power returned after a failure, resuming",
    "F1": "F1: Pellet inlet pipe overload",
    "S7": "S7: Extinguishing, first step",
    "S7-1": "S7-1: Extinguishing, waiting for flame loss",
    "S7-2": "S7-2: Extinguishing, fan at maximum",
    "S7-3": "S7-3: Standby, waiting for start conditions",
}


def test_the_stage_texts_are_pinned() -> None:
    assert pelet_set.STAGES == EXPECTED_STAGES


def test_a_stage_the_manual_does_not_list_is_not_guessed() -> None:
    # Seen in a published Pelet-set capture, not in the manual in this form.
    for code in ("M-1", "A7-1", "P2-2"):
        assert pelet_set.stage_text(code) == f"Unknown ({code})"
        assert pelet_set.stage_details(code)["stage_group"] == "unknown"


def test_the_stage_groups() -> None:
    groups = {code: pelet_set.stage_details(code)["stage_group"] for code in EXPECTED_STAGES}
    assert groups["OFF"] == "off"
    assert {groups[c] for c in ("A0", "A1", "A2", "A3", "A4", "A5", "A6", "PP1", "PP5")} == {"ignition_startup"}
    assert {groups[c] for c in ("P", "P2", "P6")} == {"nominal_power"}
    assert {groups[c] for c in ("M1", "M4")} == {"modulation"}
    assert {groups[c] for c in ("S7", "S7-1", "S7-2")} == {"shutdown"}
    assert groups["S7-3"] == "standby"
    assert groups["PFON230"] == "power_failure_recovery"
    assert pelet_set.stage_details("M3")["power_level"] == 3
    assert pelet_set.stage_details("A3")["description"] == "Waiting for flame"


@pytest.mark.parametrize(
    ("marking", "expected"),
    [
        (
            "A.7.2",
            {
                "Boiler connection": "Accumulation tank via 3-way thermostatic valve",
                "DHW": "DHW tank in the boiler",
                "Heating circuits with mixing valve": "2",
            },
        ),
        (
            "F01",
            {
                "Boiler connection": "Hydraulic crossover with sensor via 3-way valve with actuator",
                "DHW": "None",
                "Heating circuits with mixing valve": "1",
            },
        ),
        (
            "H.2.0",
            {
                "Boiler connection": "4-way valve with actuator",
                "DHW": "DHW tank with recirculation",
                "Heating circuits with mixing valve": "None",
            },
        ),
    ],
)
def test_the_configuration_marking_is_spelled_out(marking, expected) -> None:
    assert pelet_set.configuration(marking) == expected


@pytest.mark.parametrize("marking", ["", None, "G.1.1", "A.5.1", "A.1.3", "A.1", "12"])
def test_a_marking_that_is_not_one_is_left_alone(marking) -> None:
    assert pelet_set.configuration(marking) is None


def test_the_codes_are_named_after_the_manual() -> None:
    assert pelet_set.code_name("E2") == "E2 Ignition error"
    assert pelet_set.code_name("W4") == "W4 Fuel level"
    assert pelet_set.code_name("E121") == "E121 No pellets"
    assert pelet_set.code_name("W5") is None
    assert pelet_set.code_name("B_Tk1") is None


# The entities


@pytest.fixture
def hass_available():
    pytest.importorskip("homeassistant")


class _Client:
    def has_fresh_data(self) -> bool:
        return True


def _device(**parameters) -> WebBoilerDevice:
    device = WebBoilerDevice("user@example.com")
    device.update({"id": 1001, "serial": "SN000001", "type": "cmpelet", "product": "Cm Pelet-set"})
    device["__client"] = _Client()
    device["__system"] = None
    for name, value in parameters.items():
        device.create_parameter(name, value)
    return device


def test_the_boiler_state_uses_the_burner_stages(hass_available) -> None:
    from custom_components.centrometal_cloud.sensors.WebBoilerOperationStateSensor import (
        WebBoilerOperationStateSensor,
    )

    [entity] = WebBoilerOperationStateSensor.create_entities(None, _device(B_STATE="S7-3"))
    assert entity.native_value == "S7-3: Standby, waiting for start conditions"
    assert entity.extra_state_attributes["Stage group"] == "standby"


def test_the_setup_keeps_the_marking_and_spells_it_out(hass_available) -> None:
    from custom_components.centrometal_cloud.sensors.WebBoilerGenericSensor import WebBoilerGenericSensor

    device = _device(B_KONF_STR="A.7.2")
    entities = {entity.unique_id: entity for entity in WebBoilerGenericSensor.create_conf_entities(None, device)}
    setup = entities["SN000001-B_KONF_STR"]
    assert setup.native_value == "A.7.2"
    assert setup.extra_state_attributes["DHW"] == "DHW tank in the boiler"


def test_a_temperature_of_minus_55_is_unknown(hass_available) -> None:
    from custom_components.centrometal_cloud.sensors.WebBoilerGenericSensor import WebBoilerGenericSensor

    device = _device(B_Tak2="-55", B_Tk1="65.3")
    entities = {entity.unique_id: entity for entity in WebBoilerGenericSensor.create_conf_entities(None, device)}
    assert entities["SN000001-B_Tak2"].native_value is None
    assert entities["SN000001-B_Tk1"].native_value == "65.3"


def test_the_hidden_code_entities_carry_the_manual_text(hass_available) -> None:
    from custom_components.centrometal_cloud.sensors.WebBoilerGenericSensor import WebBoilerGenericSensor

    entities = {
        entity.unique_id: entity
        for entity in WebBoilerGenericSensor.create_unknown_entities(None, _device(E2="A", W4="A"))
    }
    assert entities["SN000001-E2"]._description == "E2 Ignition error"
    assert entities["SN000001-W4"]._description == "W4 Fuel level"
    assert entities["SN000001-E2"].entity_registry_enabled_default is False


def test_the_return_temperature_of_a_biotec_is_named_so(hass_available) -> None:
    from custom_components.centrometal_cloud.sensors.generic_sensors_biotec import BIOTEC_GENERIC_SENSORS
    from custom_components.centrometal_cloud.sensors.generic_sensors_biotec_plus import BIOTEC_PLUS_GENERIC_SENSORS

    assert BIOTEC_GENERIC_SENSORS["B_Tpov1"][3] == "Return Temperature"
    assert BIOTEC_PLUS_GENERIC_SENSORS["B_Tpov1"][3] == "Return Temperature"
