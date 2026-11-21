"""The realtime channel against a broker that accepts the login and refuses the subscription (issue #1).

The reporter's portal account got `ACCESS_REFUSED - read access to exchange 'amq.topic'` for its BioTec-L: the
integration logged it 67,182 times in nine hours, because the reconnect loop of `websockets` starts the next session
at once when the previous one ends without an exception. Each session also wrote the state of every entity twice.
"""

from __future__ import annotations

import asyncio
import importlib
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "custom_components" / "centrometal_cloud"))

from websockets.asyncio.server import serve  # noqa: E402

ws_module = importlib.import_module("centrometal_web_boiler.WebBoilerWsClient")
WebBoilerWsClient = ws_module.WebBoilerWsClient

REFUSED = (
    "ERROR\nmessage:access_refused\ncontent-type:text/plain\n\n"
    "ACCESS_REFUSED - read access to exchange 'amq.topic' in vhost '/' refused for user 'appuser'\x00"
)


async def _run_against(broker_answer, seconds: float, monkeypatch) -> tuple[dict, WebBoilerWsClient]:
    stats = {"sessions": 0, "errors": 0, "connected": 0, "disconnected": 0}

    async def broker(ws):
        stats["sessions"] += 1
        async for message in ws:
            if message.startswith("CONNECT"):
                await ws.send("CONNECTED\nversion:1.1\nheart-beat:0,0\n\n\x00")
            elif message.startswith("SUBSCRIBE"):
                await broker_answer(ws)
                return

    async with serve(broker, "127.0.0.1", 0) as server:
        port = server.sockets[0].getsockname()[1]
        monkeypatch.setattr(ws_module, "WEB_BOILER_STOMP_URL", f"ws://127.0.0.1:{port}/ws")
        client: WebBoilerWsClient | None = None

        async def connected(ws, frame):
            stats["connected"] += 1
            await client.subscribe_to_installation(ws, {"type": "biotec", "serial": "SN000001"})

        async def disconnected(ws, code, reason):
            stats["disconnected"] += 1

        async def error(ws, err):
            stats["errors"] += 1

        async def data(ws, frame):
            pass

        client = WebBoilerWsClient(None, connected, disconnected, error, data, ssl_context_factory=lambda: None)
        await client.start("user@example.com")
        await asyncio.sleep(seconds)
        started = asyncio.get_running_loop().time()
        await client.close()
        stats["close_seconds"] = asyncio.get_running_loop().time() - started
    return stats, client


def test_a_refused_subscription_is_not_retried_in_a_loop(monkeypatch) -> None:
    async def refuse(ws):
        await ws.send(REFUSED)
        await ws.close()

    stats, client = asyncio.run(_run_against(refuse, 1.5, monkeypatch))
    assert stats["sessions"] == 1
    assert stats["errors"] == 1
    assert (stats["connected"], stats["disconnected"]) == (1, 1), "one state write of the entities each way, not more"
    assert client.subscription_refused is True
    assert client.next_session_delay() == ws_module.REFUSED_RETRY_SECONDS
    assert stats["close_seconds"] < 1, "a stop does not wait for the pause to end"


def test_a_session_without_data_is_followed_by_a_growing_pause(monkeypatch) -> None:
    async def close_at_once(ws):
        await ws.close()

    monkeypatch.setattr(ws_module, "RECONNECT_BASE_SECONDS", 0.2)
    monkeypatch.setattr(ws_module, "next_retry_delay", lambda attempt, base, cap: base * 2**attempt)
    stats, client = asyncio.run(_run_against(close_at_once, 1.0, monkeypatch))
    # Pauses of 0.2, 0.4, 0.8 s: three sessions in one second, where the loop of `websockets` made hundreds.
    assert 2 <= stats["sessions"] <= 4
    assert client.subscription_refused is False


def test_a_session_that_carried_data_starts_the_next_one_at_once() -> None:
    client = WebBoilerWsClient(None, None, None, None, None)
    client._session_carried_data = True
    client._failed_sessions = 5
    assert client.next_session_delay() == 0


def test_the_refusal_is_recognised_from_the_frame() -> None:
    frame = {"cmd": "ERROR", "headers": {"message": "access_refused"}, "body": "ACCESS_REFUSED - read access"}
    assert ws_module.is_access_refused(frame) is True
    assert ws_module.is_access_refused({"cmd": "ERROR", "headers": {"message": "not_found"}, "body": ""}) is False
    assert ws_module.is_access_refused(ConnectionError("x")) is False


def test_repeated_errors_are_one_warning(caplog) -> None:
    client_module = importlib.import_module("centrometal_web_boiler.WebBoilerClient")
    client = client_module.WebBoilerClient()
    frame = {"cmd": "ERROR", "headers": {"message": "access_refused"}, "body": "ACCESS_REFUSED - read access"}

    async def runner() -> None:
        for _ in range(5):
            await client.ws_error_callback(None, frame)

    with caplog.at_level(logging.DEBUG):
        asyncio.run(runner())
    warnings = [r for r in caplog.records if r.levelno >= logging.WARNING]
    assert len(warnings) == 1
    assert "HTTP polling" in warnings[0].getMessage()
    assert not [r for r in caplog.records if r.levelno >= logging.ERROR]
