"""Settings slots the portal leaves out of its status snapshot are read back.

Owner's diagnostics, PelTec II Lambda v3.03dL: parameter-list listed seven
editable settings, but the status snapshot carried only some of them (on
04.11.2026 only slot 576), and the rest came back only when the settings page
was opened on the portal website. The client now asks the controller for the
missing slots with the portal's own read, "PRD <slot>": "VAL".
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "custom_components" / "centrometal_cloud"))

from centrometal_web_boiler.HttpClient import HttpClient, HttpClientConnectionError  # noqa: E402
from centrometal_web_boiler.WebBoilerClient import WebBoilerClient  # noqa: E402
from centrometal_web_boiler.WebBoilerDeviceCollection import (  # noqa: E402
    WebBoilerDevice,
    WebBoilerDeviceCollection,
)

ROWS = {str(i): {"dbindex": i, "naslov": f"Setting {i}"} for i in (576, 67, 71, 291)}


class _Http:
    def __init__(self, fail: bool = False) -> None:
        self.reads: list[tuple] = []
        self.fail = fail

    async def read_settings(self, id_, dbindexes):
        self.reads.append((id_, list(dbindexes)))
        if self.fail:
            raise HttpClientConnectionError("portal down")
        return {"status": "success"}


def _client(slots: dict[str, str], fail: bool = False) -> tuple[WebBoilerClient, WebBoilerDevice, _Http]:
    client = WebBoilerClient()
    client.data = WebBoilerDeviceCollection("user@example.com")
    device = WebBoilerDevice("user@example.com")
    device["id"] = 1001
    device["serial"] = "SN1"
    device["type"] = "peltec2"
    device["temperatures"] = dict(ROWS)
    for name, value in slots.items():
        device.create_parameter(name, value)
    client.data["SN1"] = device
    client.http_client = _Http(fail)
    return client, device, client.http_client


REPORTED_576 = {"PVAL_576_0": "5", "PMIN_576_0": "5", "PMAX_576_0": "10"}


def test_only_the_slots_without_value_or_minimum_are_missing() -> None:
    _client_, device, _http = _client({**REPORTED_576, "PVAL_67_0": "67", "PVAL_71_0": "?", "PMIN_71_0": "?"})
    # 67 has a value but no minimum; 71 only placeholders; 291 nothing at all.
    assert WebBoilerClient.missing_settings(device) == [67, 71, 291]


def test_the_missing_slots_are_requested_in_one_read() -> None:
    async def runner() -> None:
        client, _device, http = _client(REPORTED_576)
        await client._request_missing_settings(1001, now=1000.0)
        assert http.reads == [(1001, [67, 71, 291])]

    asyncio.run(runner())


def test_nothing_is_sent_when_every_slot_is_reported() -> None:
    async def runner() -> None:
        slots = {**REPORTED_576}
        for i in (67, 71, 291):
            slots.update({f"PVAL_{i}_0": "1", f"PMIN_{i}_0": "0"})
        client, _device, http = _client(slots)
        await client._request_missing_settings(1001, now=1000.0)
        assert http.reads == []

    asyncio.run(runner())


def test_the_read_is_repeated_at_most_once_an_hour() -> None:
    async def runner() -> None:
        client, _device, http = _client(REPORTED_576)
        await client._request_missing_settings(1001, now=1000.0)
        await client._request_missing_settings(1001, now=1000.0 + 240)
        await client._request_missing_settings(1001, now=1000.0 + 3599)
        assert len(http.reads) == 1
        await client._request_missing_settings(1001, now=1000.0 + 3600)
        assert len(http.reads) == 2

    asyncio.run(runner())


def test_a_failed_read_does_not_fail_the_refresh() -> None:
    async def runner() -> None:
        client, _device, http = _client(REPORTED_576, fail=True)
        await client._request_missing_settings(1001, now=1000.0)
        assert len(http.reads) == 1

    asyncio.run(runner())


def test_the_read_uses_the_portal_command_shape() -> None:
    async def runner() -> None:
        sent: list[tuple] = []
        http = HttpClient("user@example.com", "secret")

        async def control_advanced(id_, data):
            sent.append((id_, data))
            return {"status": "success"}

        http._control_advanced = control_advanced
        await http.read_settings(1001, [71, 291])
        assert sent == [(1001, {"parameters": {"PRD 71": "VAL", "PRD 291": "VAL"}})]

    asyncio.run(runner())
