"""The PelTec II boiler schedule: decoding, the calendar and the read request.

The tables are the ones a PelTec II Lambda (v3.03dL) sent when the portal read them, next to what the
portal showed for the same tables: Table 1 a start at 17:30 each day; Table 2 04:00-08:00 and
17:30-23:00; Table 3 01-03, 06-08, 12-14, 17-19 and 21-23; the selector on Off.
"""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.append(str(ROOT / "custom_components" / "centrometal_cloud"))  # after the stdlib: calendar.py is a platform

from centrometal_web_boiler.WebBoilerClient import SCHEDULE_READ_SECONDS, WebBoilerClient  # noqa: E402
from centrometal_web_boiler.WebBoilerDeviceCollection import (  # noqa: E402
    WebBoilerDevice,
    WebBoilerDeviceCollection,
)
from custom_components.centrometal_cloud import schedule  # noqa: E402

# One day of each table, as the controller sent it; every day of the capture was the same.
TABLE_1_DAY = [33818] + [1440] * 9
TABLE_2_DAY = [33008, 480, 1440, 1440, 33818, 1380, 1440, 1440, 1440, 1440]
TABLE_3_DAY = [32828, 180, 33128, 480, 33488, 840, 33788, 1140, 34028, 1380]
TZ = ZoneInfo("Europe/Bucharest")


def _slots(selector=0, tables=(TABLE_1_DAY, TABLE_2_DAY, TABLE_3_DAY)) -> dict[str, int]:
    values = {"PVAL_223_0": selector}
    for slot, day in zip((224, 225, 226), tables, strict=True):
        for index, value in enumerate(day * 7):
            values[f"PVAL_{slot}_{index}"] = value
    return values


def test_a_start_carries_bit_15_and_1440_is_unused() -> None:
    assert schedule.day_windows(TABLE_2_DAY) == [(240, 480), (1050, 1380)]
    assert schedule.day_windows(TABLE_3_DAY) == [(60, 180), (360, 480), (720, 840), (1020, 1140), (1260, 1380)]
    assert schedule.day_windows([1440] * 10) == []


def test_a_start_without_a_stop_runs_to_the_end_of_the_day() -> None:
    assert schedule.day_windows(TABLE_1_DAY) == [(1050, 1440)]
    assert schedule.describe_day(schedule.day_windows(TABLE_1_DAY)) == "17:30-24:00"


def test_the_tables_read_as_the_portal_showed_them() -> None:
    values = _slots()
    assert schedule.describe_day(schedule.table_windows(values, 2)[0]) == "04:00-08:00, 17:30-23:00"
    assert schedule.describe_day(schedule.table_windows(values, 3)[6]) == (
        "01:00-03:00, 06:00-08:00, 12:00-14:00, 17:00-19:00, 21:00-23:00"
    )


def test_a_table_is_unknown_until_every_value_has_arrived() -> None:
    values = _slots()
    del values["PVAL_225_69"]
    assert schedule.table_windows(values, 2) is None
    assert schedule.table_windows(values, 1) is not None


def test_the_selector_reads_off_or_a_table() -> None:
    assert schedule.active_table({"PVAL_223_0": 0}) == 0
    assert schedule.active_table({"PVAL_223_0": "2"}) == 2
    assert schedule.active_table({"PVAL_223_0": {"value": "3"}}) == 3
    assert schedule.active_table({}) is None
    assert schedule.active_table({"PVAL_223_0": "7"}) is None


def test_only_the_schedule_values_are_schedule_parameters() -> None:
    assert schedule.is_schedule_parameter("PVAL_223_0")
    assert schedule.is_schedule_parameter("PVAL_226_69")
    assert not schedule.is_schedule_parameter("PVAL_67_0")
    assert not schedule.is_schedule_parameter("PMIN_224_0")


def test_occurrences_follow_the_weekday_and_the_local_time() -> None:
    week = schedule.table_windows(_slots(), 2)
    monday = datetime(2026, 11, 23, tzinfo=TZ)
    found = schedule.occurrences(week, monday, monday + timedelta(days=1), TZ)
    assert found == [
        (monday.replace(hour=4), monday.replace(hour=8)),
        (monday.replace(hour=17, minute=30), monday.replace(hour=23)),
    ]


def test_an_occurrence_from_the_day_before_still_counts_when_it_overlaps() -> None:
    week = schedule.table_windows(_slots(), 1)
    late = datetime(2026, 11, 24, 0, 0, tzinfo=TZ) - timedelta(minutes=1)
    found = schedule.occurrences(week, late, late + timedelta(minutes=30), TZ)
    assert found == [(datetime(2026, 11, 23, 17, 30, tzinfo=TZ), datetime(2026, 11, 24, 0, 0, tzinfo=TZ))]


# The read


class _Http:
    def __init__(self, fail: bool = False) -> None:
        self.reads: list[tuple] = []
        self.fail = fail

    async def get_table_data(self, id_, start, table):
        self.reads.append((id_, start, table))
        if self.fail:
            from centrometal_web_boiler.HttpClient import HttpClientConnectionError

            raise HttpClientConnectionError("portal down")
        return {"status": "success"}


def _client(device_type: str = "peltec2", fail: bool = False) -> tuple[WebBoilerClient, _Http]:
    client = WebBoilerClient()
    client.data = WebBoilerDeviceCollection("user@example.com")
    device = WebBoilerDevice("user@example.com")
    device["id"] = 1001
    device["serial"] = "SN1"
    device["type"] = device_type
    client.data["SN1"] = device
    client.http_client = _Http(fail)
    return client, client.http_client


def test_the_schedule_is_read_like_the_portal_reads_it() -> None:
    client, http = _client()
    asyncio.run(client._request_schedule(1001, now=1000.0, delay=0))
    # {"PRD 223": "VAL", "PRD 224": "ALV"}, then 225 and 226.
    assert http.reads == [(1001, 223, 1), (1001, 223, 2), (1001, 223, 3)]


def test_the_schedule_is_read_every_six_hours_only() -> None:
    client, http = _client()
    asyncio.run(client._request_schedule(1001, now=1000.0, delay=0))
    asyncio.run(client._request_schedule(1001, now=1000.0 + SCHEDULE_READ_SECONDS - 1, delay=0))
    assert len(http.reads) == 3
    asyncio.run(client._request_schedule(1001, now=1000.0 + SCHEDULE_READ_SECONDS, delay=0))
    assert len(http.reads) == 6


def test_only_a_peltec_ii_is_asked_for_its_schedule() -> None:
    client, http = _client(device_type="peltec")
    asyncio.run(client._request_schedule(1001, now=1000.0, delay=0))
    assert http.reads == []


def test_a_failed_read_stops_quietly() -> None:
    client, http = _client(fail=True)
    asyncio.run(client._request_schedule(1001, now=1000.0, delay=0))
    assert len(http.reads) == 1


def test_the_read_request_has_the_portal_shape() -> None:
    from centrometal_web_boiler.HttpClient import HttpClient

    sent: list = []
    http = HttpClient("user@example.com", "secret")

    async def control_advanced(id_, data):
        sent.append((id_, data))
        return {"status": "success"}

    http._control_advanced = control_advanced
    asyncio.run(http.get_table_data(1001, 223, 2))
    assert sent == [(1001, {"parameters": {"PRD 223": "VAL", "PRD 225": "ALV"}})]


# The calendar


@pytest.fixture
def calendar_entity():
    pytest.importorskip("homeassistant")
    from homeassistant.util import dt as dt_util

    from custom_components.centrometal_cloud.calendar import WebBoilerScheduleCalendar

    class _Fresh:
        data = WebBoilerDeviceCollection("user@example.com")

        def has_fresh_data(self) -> bool:
            return True

    device = WebBoilerDevice("user@example.com")
    device.update({"id": 1001, "serial": "SN1", "type": "peltec2", "product": "PelTec II Lambda"})
    device["__client"] = _Fresh()
    saved = dt_util.get_default_time_zone()
    dt_util.set_default_time_zone(TZ)
    yield WebBoilerScheduleCalendar(None, device), device
    dt_util.set_default_time_zone(saved)


def _fill(device, selector) -> None:
    for name, value in _slots(selector).items():
        device.create_parameter(name, value)


def test_the_calendar_shows_the_active_table(calendar_entity) -> None:
    entity, device = calendar_entity
    _fill(device, selector=3)
    monday = datetime(2026, 11, 23, tzinfo=TZ)
    events = asyncio.run(entity.async_get_events(None, monday, monday + timedelta(days=1)))
    assert [(e.start.hour, e.end.hour) for e in events] == [(1, 3), (6, 8), (12, 14), (17, 19), (21, 23)]
    assert events[0].summary == "Boiler on (Table 3)"
    attributes = entity.extra_state_attributes
    assert attributes["Active table"] == "Table 3"
    assert attributes["Table 2"]["Mon"] == "04:00-08:00, 17:30-23:00"


def test_with_the_selector_off_the_calendar_has_no_events(calendar_entity) -> None:
    entity, device = calendar_entity
    _fill(device, selector=0)
    monday = datetime(2026, 11, 23, tzinfo=TZ)
    assert asyncio.run(entity.async_get_events(None, monday, monday + timedelta(days=7))) == []
    assert entity.event is None
    assert entity.extra_state_attributes["Active table"] == "Off"
    assert entity.available is True


def test_the_calendar_is_unavailable_until_the_selector_is_known(calendar_entity) -> None:
    entity, _device = calendar_entity
    assert entity.available is False


def test_the_capture_matches_the_fixture_snapshot() -> None:
    """The older portal snapshot in the fixtures holds the same Table 1."""
    snapshot = json.loads((ROOT / "tests" / "fixtures" / "peltec2_lambda_http_snapshot.json").read_text())
    assert [int(snapshot[f"PVAL_224_{i}"]) for i in range(10)] == TABLE_1_DAY
