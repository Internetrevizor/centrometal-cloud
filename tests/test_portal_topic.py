"""The portal's realtime topic since 14.11.2026, and installations without a product name.

Since 14.11.2026 the portal refuses "/topic/cm.inst.<type>.<serial>" with ACCESS_REFUSED (read access to exchange
'amq.topic'); its realtime data is on the "stomp" exchange.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from custom_components.centrometal_cloud.centrometal_web_boiler.WebBoilerDeviceCollection import (  # noqa: E402
    DEFAULT_PRODUCT,
    WebBoilerDevice,
    WebBoilerDeviceCollection,
)
from custom_components.centrometal_cloud.centrometal_web_boiler.WebBoilerWsClient import WebBoilerWsClient  # noqa: E402

SERIAL = "SN000001"


def test_the_subscription_uses_the_stomp_exchange() -> None:
    sent: list[str] = []

    class Socket:
        async def send(self, frame: str) -> None:
            sent.append(frame)

    client = WebBoilerWsClient(None, None, None, None, None)
    asyncio.run(client.subscribe_to_installation(Socket(), {"type": "peltec2", "serial": SERIAL}))
    assert f"destination:/exchange/stomp/cm.inst.peltec2.{SERIAL}\n" in sent[0]
    assert "/topic/" not in sent[0]


def _collection() -> tuple[WebBoilerDeviceCollection, WebBoilerDevice]:
    collection = WebBoilerDeviceCollection("user@example.com")
    collection.parse_installations(
        [{"value": 1001, "label": SERIAL, "place": "Example City", "address": "", "type": "peltec2", "product": "X"}]
    )
    return collection, collection[SERIAL]


def test_a_message_on_the_stomp_exchange_is_read() -> None:
    collection, device = _collection()
    frame = {
        "headers": {"subscription": "sub-1", "destination": f"/exchange/stomp/cm.inst.peltec2.{SERIAL}"},
        "body": '{"B_Tk1":"31.5"}',
    }
    asyncio.run(collection.parse_real_time_frame(frame))
    assert device.get_parameter("B_Tk1")["value"] == "31.5"


def test_a_message_with_the_old_destination_is_still_read() -> None:
    collection, device = _collection()
    frame = {"headers": {"subscription": "sub-1", "destination": f"/topic/cm.inst.peltec2.{SERIAL}"}, "body": '{"B_Tk1":"30"}'}
    asyncio.run(collection.parse_real_time_frame(frame))
    assert device.get_parameter("B_Tk1")["value"] == "30"


def test_an_installation_without_product_place_or_address_is_set_up() -> None:
    """KeyError 'product' stopped the setup."""
    collection = WebBoilerDeviceCollection("user@example.com")
    collection.parse_installations([{"value": 1001, "label": SERIAL, "type": "peltec"}])
    device = collection[SERIAL]
    assert device["product"] == DEFAULT_PRODUCT
    assert (device["place"], device["address"]) == ("", "")
