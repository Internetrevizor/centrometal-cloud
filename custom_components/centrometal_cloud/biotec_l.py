"""BioTec-L: operation phases, error, warning and information codes, missing sensors.

Everything here comes from the controller manual, "Technical instructions REGULATION BioTec-L":

* the operation phases, from "5.0. Operation phases (shown on the screen)", pages 60-62. They are not
  the PelTec II stages: S1 is the second ignition step here, and DIF, GLW, DOP0 and OFF1 exist only here;
* the codes, from "6.1. List and elimination of errors / warnings / informations", pages 64-72.
  E is an error, W a warning, I an information (page 30);
* a sensor the controller cannot read is shown as "-" on its screen instead of a temperature (errors E1
  and E2, page 64). Through the portal a BioTec-L reported -55 for its mixer and DHW temperatures and for
  B_Ths1 at once, a value no water or room temperature reaches.

The texts are Home Assistant state texts, so automations compare against them:
tests/test_biotec_l.py pins every one.
"""

from __future__ import annotations

from typing import Any

# Operation phases. "DX" in the manual is the common name of D4 to D1; the screen shows one of them.
STAGES: dict[str, str] = {
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

# "PF-" in front of any phase: the boiler is in that phase after a power failure (page 62).
POWER_FAILURE_PREFIX = "PF-"

CODES: dict[str, str] = {
    "E1": "DHW sensor",
    "E2": "Buffer tank sensor (upper)",
    "E3": "Buffer tank sensor (lower)",
    "E4": "Flue gas sensor",
    "E5": "Outside temperature sensor",
    "E6": "Main flow sensor",
    "E7": "Return flow sensor",
    "E8": "Boiler sensor",
    "E9": "Unknown boiler power",
    "E10": "Fan error",
    "E12": "Communication error with motherboard",
    "E13": "Communication error with sensor board",
    "E14": "Lambda probe error",
    "E16": "Communication error with CM2K (1+ and 2+)",
    "E17": "CM2K 1+ circuit sensor",
    "E18": "CM2K 1+ circuit corrector",
    "E19": "CM2K 2+ circuit sensor",
    "E20": "CM2K 2+ circuit corrector",
    "E21": "Firebox sensor",
    "E24": "Room corrector error",
    "E26": "Firebox sensor disconnected",
    "E27": "Hydraulic crossover sensor error",
    "E29": "Communication error with WiFi",
    "W1": "Factory settings loaded",
    "W2": "Flue gas temperature high, close the upper door",
    "W3": "Fan protection",
    "W4": "Intervention work (firebox sensor)",
    "W5": "Intervention work (lambda probe)",
    "W6": "Intervention work (flue gas sensor)",
    "W7": "Intervention work (RPM sensor)",
    "W8": "Ignition error, try again",
    "W9": "Fan off, flue gas temperature too high, close the upper door",
    "W10": "Low return temperature",
    "W11": "Out of fuel",
    "W12": "Low buffer temperature",
    "I1": "OFF during ignition",
    "I2": "Ignition automatically proceeded",
    "I3": "Bad ignition",
    "I4": "OFF during stabilisation",
    "I5": "Power up after a power failure",
    "I6": "Glow after power up",
    "I7": "OFF after power up",
}

# The portal sends -55 for a sensor the controller cannot read. The PelTec II portal pages accept nothing at or
# below -45 for water, room, buffer and outside temperatures (see peltec2.valid_temperature); the same bound is
# used here.
LOWEST_TEMPERATURE = -45.0


def is_biotec_l(device: Any) -> bool:
    """A BioTec-L: the portal type "biotec" and the product name. Other "biotec" products have other manuals."""
    if device.get("type") != "biotec":
        return False
    product = str(device.get("product") or "")
    return "biotec-l" in product.lower()


def stage_text(code: str) -> str:
    if code in STAGES:
        return STAGES[code]
    if code.startswith(POWER_FAILURE_PREFIX):
        phase = code[len(POWER_FAILURE_PREFIX) :]
        if phase in STAGES:
            return f"{code}: Power failure — {_description(STAGES[phase])}"
    return f"Unknown ({code})"


def _description(text: str) -> str:
    return text.split(": ", 1)[1] if ": " in text else text


def stage_details(code: str) -> dict[str, object]:
    """The attributes of the Boiler State sensor, in the shape the PelTec II one has."""
    phase = code[len(POWER_FAILURE_PREFIX) :] if code.startswith(POWER_FAILURE_PREFIX) else code
    power_level = int(phase[1:]) if phase in {"D1", "D2", "D3", "D4"} else None
    if code.startswith(POWER_FAILURE_PREFIX):
        group = "power_failure_recovery"
    elif code == "OFF":
        group = "off"
    elif code in {"S0", "S1", "SP1", "SP2", "SD4"}:
        group = "ignition_startup"
    elif power_level is not None:
        group = "modulation"
    elif code == "DOP0":
        group = "door_open"
    elif code.startswith("DIF"):
        group = "differential"
    elif code.startswith("GLW"):
        group = "glow"
    elif code == "OFF1":
        group = "shutdown"
    else:
        group = "unknown"
    text = stage_text(code)
    return {
        "raw_stage": code,
        "stage_group": group,
        "description": text if text.startswith("Unknown") else _description(text),
        "power_level": power_level,
    }


def code_name(parameter: str) -> str | None:
    """ "W11 Out of fuel" for the parameter W11; None for a parameter that is not a code the manual lists."""
    text = CODES.get(parameter)
    return f"{parameter} {text}" if text else None


def valid_temperature(value: Any) -> float | None:
    """The temperature, or None for a sensor the controller does not read (-55)."""
    try:
        numeric = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    if numeric != numeric or numeric <= LOWEST_TEMPERATURE:
        return None
    return numeric
