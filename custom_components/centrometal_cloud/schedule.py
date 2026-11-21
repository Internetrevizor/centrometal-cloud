"""The PelTec II boiler schedule: three weekly tables and the selector of the active one.

Layout, from the controller manual ("Technical instructions Controller PelTec II Lambda", 2.2 Boiler
schedule, pages 30-31) and checked against a capture of a PelTec II Lambda (v3.03dL) read through the
portal:

* slot 223 is the selector: 0 Off, 1 Table 1, 2 Table 2, 3 Table 3. Only Off was seen; the numbers of
  the tables follow the order the manual and the portal list them in;
* slots 224, 225 and 226 are Table 1, 2 and 3. Each holds 70 values, ``PVAL_<slot>_0`` to ``_69``:
  seven days from Monday, ten values a day, the five starts and five stops T1-T5;
* a value is a time in minutes after midnight. A start carries bit 15 (32768) as well, a stop does
  not; 1440 marks an unused value. 33008 is a start at 04:00 (32768 + 240), 480 a stop at 08:00.

The portal reads a table with ``{"PRD 223": "VAL", "PRD 224": "ALV"}``: the selector and the whole
table, in one request.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime, time, timedelta, tzinfo
from typing import Any

SELECTOR_SLOT = 223
TABLE_SLOTS = {1: 224, 2: 225, 3: 226}
SCHEDULE_SLOTS = frozenset({SELECTOR_SLOT, *TABLE_SLOTS.values()})

VALUES_PER_DAY = 10
DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
START_FLAG = 0x8000
UNUSED = 1440
END_OF_DAY = 1440

# A window: start and end in minutes after midnight, the end exclusive.
Window = tuple[int, int]


def is_schedule_parameter(name: str) -> bool:
    """``PVAL_223_0`` to ``PVAL_226_69``: the values this module decodes."""
    parts = name.split("_")
    return len(parts) == 3 and parts[0] == "PVAL" and parts[1] in {str(slot) for slot in SCHEDULE_SLOTS}


def _int(value: Any) -> int | None:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def active_table(parameters: Mapping[str, Any]) -> int | None:
    """0 for Off, 1-3 for the active table, None while the selector has not been reported."""
    selector = _int(_value(parameters, f"PVAL_{SELECTOR_SLOT}_0"))
    if selector is None or not 0 <= selector <= 3:
        return None
    return selector


def _value(parameters: Mapping[str, Any], name: str) -> Any:
    parameter = parameters.get(name)
    # Device parameters are dicts with a "value"; tests pass plain values.
    return parameter.get("value") if isinstance(parameter, Mapping) else parameter


def day_windows(values: list[Any]) -> list[Window]:
    """The windows of one day, from its ten values in table order.

    A start opens a window and the next stop closes it. A start with no stop after it runs to the end
    of the day: Table 1 of the captured boiler holds a single start at 17:30 each day.
    """
    windows: list[Window] = []
    opened: int | None = None
    for raw in values:
        value = _int(raw)
        if value is None:
            continue
        minutes = value & ~START_FLAG
        if minutes >= UNUSED:
            continue
        if value & START_FLAG:
            if opened is None:
                opened = minutes
        elif opened is not None and minutes > opened:
            windows.append((opened, minutes))
            opened = None
    if opened is not None:
        windows.append((opened, END_OF_DAY))
    return windows


def table_windows(parameters: Mapping[str, Any], table: int) -> list[list[Window]] | None:
    """The windows of each day of one table, Monday first; None until the table has been reported."""
    slot = TABLE_SLOTS[table]
    names = [f"PVAL_{slot}_{index}" for index in range(7 * VALUES_PER_DAY)]
    values = [_value(parameters, name) for name in names]
    if any(value is None for value in values):
        return None
    return [day_windows(values[day * VALUES_PER_DAY : (day + 1) * VALUES_PER_DAY]) for day in range(7)]


def format_minutes(minutes: int) -> str:
    return "24:00" if minutes >= END_OF_DAY else f"{minutes // 60:02d}:{minutes % 60:02d}"


def describe_day(windows: list[Window]) -> str:
    if not windows:
        return "-"
    return ", ".join(f"{format_minutes(start)}-{format_minutes(end)}" for start, end in windows)


def occurrences(week: list[list[Window]], start: datetime, end: datetime, tz: tzinfo) -> list[tuple[datetime, datetime]]:
    """Every window of a weekly table that overlaps [start, end), in the controller's time zone."""
    found: list[tuple[datetime, datetime]] = []
    day: date = start.astimezone(tz).date() - timedelta(days=1)
    last: date = end.astimezone(tz).date()
    while day <= last:
        midnight = datetime.combine(day, time(0), tz)
        for begin, finish in week[day.weekday()]:
            window_start = midnight + timedelta(minutes=begin)
            window_end = midnight + timedelta(minutes=finish)
            if window_start < end and window_end > start:
                found.append((window_start, window_end))
        day += timedelta(days=1)
    return found
