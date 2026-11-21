"""The PelTec II boiler schedule as a read-only calendar.

The calendar shows the windows of the table the controller's "Boiler schedule" selector has active, as
weekly events in Home Assistant's time zone (the controller keeps local time). With the selector on Off
it has no events. Every table is also in the attributes, one line per day. The tables are changed on
the boiler or on the portal, not here. See schedule.py for the layout.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .common import create_device_info, format_name
from .schedule import DAYS, TABLE_SLOTS, active_table, describe_day, is_schedule_parameter, occurrences, table_windows


async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities):
    client = config_entry.runtime_data.client
    entities = [
        WebBoilerScheduleCalendar(hass, device) for device in client.data.values() if device.get("type") == "peltec2"
    ]
    if entities:
        async_add_entities(entities)


class WebBoilerScheduleCalendar(CalendarEntity):
    """The active table of the boiler schedule."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:calendar-clock"

    def __init__(self, hass: HomeAssistant, device) -> None:
        self.hass = hass
        self.web_boiler_client = device["__client"]
        self._device = device
        self._serial = device["serial"]
        self._attr_name = format_name(hass, device, f"{device['product']} Boiler Schedule")
        self._attr_unique_id = f"{self._serial}_calendar_boiler_schedule"

    async def async_added_to_hass(self) -> None:
        # The tables arrive in many realtime messages, long after setup; one
        # listener on the collection sees each of their values arrive.
        self.web_boiler_client.data.set_on_update_callback(self._parameter_updated, self._attr_unique_id)

    async def async_will_remove_from_hass(self) -> None:
        self.web_boiler_client.data.set_on_update_callback(None, self._attr_unique_id)

    async def _parameter_updated(self, device, parameter, _create: bool = False) -> None:
        if device is self._device and is_schedule_parameter(str(parameter.get("name", ""))):
            self.async_write_ha_state()

    @property
    def should_poll(self) -> bool:
        return False

    @property
    def available(self) -> bool:
        return self.web_boiler_client.has_fresh_data() and active_table(self._parameters) is not None

    @property
    def _parameters(self) -> dict[str, Any]:
        return self._device.get("parameters", {})

    def _active_week(self):
        table = active_table(self._parameters)
        if not table:
            return None, table
        return table_windows(self._parameters, table), table

    def _events(self, start: datetime, end: datetime) -> list[CalendarEvent]:
        week, table = self._active_week()
        if week is None:
            return []
        summary = f"Boiler on (Table {table})"
        return [
            CalendarEvent(start=begin, end=finish, summary=summary)
            for begin, finish in occurrences(week, start, end, dt_util.get_default_time_zone())
        ]

    @property
    def event(self) -> CalendarEvent | None:
        """The window running now, or else the next one within a week."""
        now = dt_util.now()
        upcoming = [event for event in self._events(now, now + timedelta(days=8)) if event.end > now]
        return min(upcoming, key=lambda event: event.start, default=None)

    async def async_get_events(self, hass: HomeAssistant, start_date: datetime, end_date: datetime) -> list[CalendarEvent]:
        return self._events(start_date, end_date)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        table = active_table(self._parameters)
        attrs: dict[str, Any] = {"Active table": "Off" if table == 0 else f"Table {table}" if table else None}
        for number in TABLE_SLOTS:
            week = table_windows(self._parameters, number)
            if week is not None:
                attrs[f"Table {number}"] = {day: describe_day(windows) for day, windows in zip(DAYS, week, strict=True)}
        return attrs

    @property
    def device_info(self):
        return create_device_info(self._device)
