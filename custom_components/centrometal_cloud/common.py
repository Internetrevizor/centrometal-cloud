from __future__ import annotations

import datetime

from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
import homeassistant.util.dt as dt_util

from .const import DOMAIN

TIMESTAMP_FORMAT = "%d.%m.%Y %H:%M:%S"


def display_value(value, fallback: str = "?") -> str:
    """Render a parameter value for display without swallowing falsy values.

    ``value or fallback`` turned a real ``0`` (and an empty string) into the
    literal text "None", which is how a 0 kW rated power or a 0-valued
    attribute ended up reported as missing. The fallback stays "?" so a
    parameter the controller has not sent reads exactly as it did before --
    device names and attributes must not change text over this fix.
    """
    if value is None or value == "":
        return fallback
    return value


def create_device_info(device) -> DeviceInfo:
    # Read through the parameters dict rather than device.get_parameter(),
    # which creates a placeholder parameter as a side effect — this runs from
    # entity properties, and a property must not mutate the cache.
    parameters = device.get("parameters", {})
    power = display_value((parameters.get("B_sng") or {}).get("value"))
    firmware_ver = display_value((parameters.get("B_VER") or {}).get("value"))
    model = f"{device['product']} {power}"
    return DeviceInfo(
        identifiers={(DOMAIN, device["serial"])},
        name=device_name(device),
        manufacturer="Centrometal",
        model=model,
        sw_version=firmware_ver,
        configuration_url="https://www.web-boiler.com",
    )


def format_time(hass: HomeAssistant, timestamp, tzinfo=None) -> str:
    """Format a UTC epoch timestamp in the user's local time zone.

    Uses dt_util.as_local() rather than dt_util.get_time_zone(): the latter
    resolves a zone name through zoneinfo, which reads from disk and trips
    Home Assistant's blocking-call detector when called from an entity
    property. as_local() uses the time zone core already resolved at startup.
    """
    dt = datetime.datetime.fromtimestamp(timestamp, tz=datetime.UTC)
    if tzinfo is not None:
        return dt.astimezone(tzinfo).strftime(TIMESTAMP_FORMAT)
    return dt_util.as_local(dt).strftime(TIMESTAMP_FORMAT)


def device_name(device) -> str:
    """The device's name: "<prefix><serial, with several boilers><product>".

    Home Assistant puts it in front of every entity's own name and builds the entity_ids from both, so a new install
    gets the entity_ids that the names "<prefix><serial> <product> <what it is>" gave before Home Assistant 2026.10.
    """
    name = device["product"].replace("GMX EASY", "biotec")
    if device.get("__multi_device"):
        name = f"{device['serial']} {name}"
    return f"{device.get('__prefix', '')}{name}"


def format_name(hass: HomeAssistant, device, name) -> str:
    """The entity's own name: "<product> <what it is>" without the product, which the device name carries."""
    product = device.get("product")
    if product and name.startswith(f"{product} "):
        name = name[len(product) + 1 :]
    return name
