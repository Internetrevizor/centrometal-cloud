"""Cm Pelet-set (portal type "cmpelet"): configuration, burner working stages, error and warning codes.

Everything here comes from the controller manual "Technical instructions CONTROLLER - CPREG-Touch"
(TU-R-CPREG-T-04-2023, EKO-CK P + Cm Pelet-set):

* the configuration marking XYZ, from "13. Heating configuration (markings on the display)", pages 50-51.
  The portal sends it as ``B_KONF_STR``, with dots: "A.7.2";
* the burner working stages, from "12. Burner working stages", page 49;
* the codes, from "14.1 List and troubleshooting of errors" and "14.2 ... of warnings", pages 95-105.

A capture of a Pelet-set published by scr34m/centrometal-reverse-engineering also shows stage codes the manual
does not list in that form ("M-1", "A7-1", "P2-2"). They are reported as "Unknown (<code>)" rather than guessed.
The texts are Home Assistant state texts: tests/test_pelet_set.py pins every one.
"""

from __future__ import annotations

from typing import Any

# X: how the boiler is connected to the heating installation (return line safety).
CONNECTIONS: dict[str, str] = {
    "A": "Accumulation tank via 3-way thermostatic valve",
    "B": "Accumulation tank via 3-way valve with actuator",
    "C": "Hydraulic crossover via 3-way thermostatic valve",
    "D": "Hydraulic crossover via 3-way valve with actuator",
    "E": "Hydraulic crossover with sensor via 3-way thermostatic valve",
    "F": "Hydraulic crossover with sensor via 3-way valve with actuator",
    "H": "4-way valve with actuator",
    "I": "Accumulation tank via 4-way valve with actuator",
    "J": "Hydraulic crossover via 4-way valve with actuator",
    "K": "Hydraulic crossover with sensor via 4-way valve with actuator",
}

# Y: the DHW the boiler controller runs.
DHW: dict[str, str] = {
    "0": "None",
    "1": "DHW tank",
    "2": "DHW tank with recirculation",
    "7": "DHW tank in the boiler",
    "8": "DHW tank in the boiler with recirculation",
}

# Z: heating circuits with a mixing valve the boiler controller runs (CM2K modules not counted).
MIXING_CIRCUITS: dict[str, str] = {
    "0": "None",
    "1": "1",
    "2": "2",
}

STAGES: dict[str, str] = {
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

CODES: dict[str, str] = {
    "E0": "Communication error with motherboard",
    "E1": "Pressure switch",
    "E2": "Ignition error",
    "E2_1": "Ignition error after power failure",
    "E3": "Pellet supply tube temperature too high",
    "E4": "Boiler sensor",
    "E5": "DHW sensor",
    "E6": "Flame loss while working",
    "E6_1": "Flame loss after power failure",
    "E7": "Wrong date and time",
    "E8": "Fan malfunction",
    "E9": "Supply tube backfilled with pellets",
    "E9_1": "Supply tube backfilled with pellets",
    "E9_2": "Supply tube backfilled with pellets",
    "E10": "Buffer tank sensor (upper)",
    "E11": "Buffer tank sensor (lower)",
    "E12": "Hydraulic crossover sensor",
    "E13": "Return line sensor",
    "E14": "Outside temperature sensor",
    "E15": "1st circuit sensor",
    "E16": "1st circuit corrector",
    "E17": "2nd circuit sensor",
    "E18": "2nd circuit corrector",
    "E19": "Photocell error",
    "E20": "Safety thermostat",
    "E21": "Recirculation sensor",
    "E22": "Unknown boiler power",
    "E23": "Wrong boiler power",
    "E24": "Fuel level",
    "E100_1": "Communication error with CM2K (1+ and 2+)",
    "E100_2": "Communication error with CM2K (3+ and 4+)",
    "E100_3": "Communication error with CM2K (5+ and 6+)",
    "E100_5": "Communication error with CMGSM",
    "E100_6": "Communication error with CM WiFi module",
    "E100_7": "Communication error with CMNET",
    "E100_8": "Communication error with CMVAC",
    "E101": "CM2K 1+ circuit sensor",
    "E102": "CM2K 1+ circuit corrector",
    "E103": "CM2K 2+ circuit sensor",
    "E104": "CM2K 2+ circuit corrector",
    "E105": "CM2K 3+ circuit sensor",
    "E106": "CM2K 3+ circuit corrector",
    "E107": "CM2K 4+ circuit sensor",
    "E108": "CM2K 4+ circuit corrector",
    "E109": "CM2K 5+ circuit sensor",
    "E110": "CM2K 5+ circuit corrector",
    "E111": "CM2K 6+ circuit sensor",
    "E112": "CM2K 6+ circuit corrector",
    "E119": "Fuel sensor",
    "E120": "Flap not closed",
    "E121": "No pellets",
    "W1": "Factory parameters loaded",
    "W2": "Wrong date and time",
    "W3": "Low return temperature",
    "W4": "Fuel level",
}


def is_pelet_set(device: Any) -> bool:
    return device.get("type") == "cmpelet"


def configuration(value: Any) -> dict[str, str] | None:
    """The three parts of a configuration marking ("A.7.2" or "A72"); None when it is not one."""
    marking = "".join(str(value or "").split(".")).strip().upper()
    if len(marking) != 3:
        return None
    connection, dhw, circuits = (CONNECTIONS.get(marking[0]), DHW.get(marking[1]), MIXING_CIRCUITS.get(marking[2]))
    if connection is None or dhw is None or circuits is None:
        return None
    return {
        "Boiler connection": connection,
        "DHW": dhw,
        "Heating circuits with mixing valve": circuits,
    }


def stage_text(code: str) -> str:
    return STAGES.get(code, f"Unknown ({code})")


def stage_details(code: str) -> dict[str, object]:
    """The attributes of the Boiler State sensor, in the shape the PelTec II one has."""
    power_level = int(code[1:]) if code in {"M1", "M2", "M3", "M4"} else None
    if code == "OFF":
        group = "off"
    elif code in {"A0", "A1", "A2", "A3", "A4", "A5", "A6"} or code.startswith("PP") and code in STAGES:
        group = "ignition_startup"
    elif code == "P" or code in {"P2", "P3", "P4", "P5", "P6"}:
        group = "nominal_power"
    elif power_level is not None:
        group = "modulation"
    elif code == "S7-3":
        group = "standby"
    elif code in {"S7", "S7-1", "S7-2"}:
        group = "shutdown"
    elif code == "PFON230":
        group = "power_failure_recovery"
    elif code == "F1":
        group = "overload"
    else:
        group = "unknown"
    text = stage_text(code)
    return {
        "raw_stage": code,
        "stage_group": group,
        "description": text.split(": ", 1)[1] if code in STAGES else text,
        "power_level": power_level,
    }


def code_name(parameter: str) -> str | None:
    text = CODES.get(parameter)
    return f"{parameter} {text}" if text else None
