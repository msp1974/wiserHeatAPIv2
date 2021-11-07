from . import _LOGGER

from device import _WiserDevice
from helpers import _to_wiser_temp, _from_wiser_temp
from schedule import _WiserSchedule
from rest_controller import _WiserRestController

from const import (
    MAX_BOOST_INCREASE,
    TEMP_MINIMUM,
    TEMP_MAXIMUM,
    TEMP_OFF,
    TEXT_OFF,
    TEXT_ON,
    TEXT_UNKNOWN,
    WiserModeEnum,
    WISERROOM
)

from datetime import datetime, timezone
import inspect


class _WiserRoom(object):
    """Class representing a Wiser Room entity"""

    def __init__(self, wiser_rest_controller:_WiserRestController, data: dict, schedule: _WiserSchedule, devices: _WiserDevice):
        self._wiser_rest_controller = wiser_rest_controller
        self._data = data
        self._schedule = schedule
        self._devices = devices
        self._mode = WiserModeEnum(data.get("Mode"))
        self._name = data.get("Name")
        self._window_detection_active = data.get("WindowDetectionActive", TEXT_UNKNOWN)

    def _send_command(self, cmd: dict):
        """
        Send control command to the room
        param cmd: json command structure
        return: boolen
        """
        result = self._wiser_rest_controller._send_command(WISERROOM.format(self.id), cmd)
        if result:
            _LOGGER.info(
                "Wiser room - {} command successful - {}".format(inspect.stack()[1].function, result)
            )
        return result

    @property
    def away_mode_suppressed(self):
        return self._data.get("AwayModeSuppressed", TEXT_UNKNOWN)

    @property
    def boost_end_time(self) -> datetime:
        """Get boost end timestamp"""
        return datetime.fromtimestamp(self._data.get("OverrideTimeoutUnixTime", 0))

    @property
    def boost_time_remaining(self) -> datetime:
        """Get boost time remaining"""
        if self.is_boosted:
            return (self.boost_end_time - datetime.now()).total_seconds()
        else:
            return 0

    @property
    def current_target_temperature(self) -> float:
        """Get current target temperature for the room"""
        return _from_wiser_temp(self._data.get("CurrentSetPoint", TEMP_MINIMUM))

    @property
    def current_temperature(self) -> float:
        """Get current temperature of the room"""
        return _from_wiser_temp(self._data.get("CalculatedTemperature", TEMP_MINIMUM))

    @property
    def devices(self):
        """Get devices associated with the room"""
        return self._devices

    @property
    def heating_rate(self):
        """Get room heating rate"""
        return self._data.get("HeatingRate", TEXT_UNKNOWN)

    @property
    def id(self) -> int:
        """Get the id of the room"""
        return self._data.get("id")

    @property
    def is_boosted(self) -> bool:
        """Get if the room temperature is currently boosted"""
        return (
            True
            if self._data.get("SetpointOrigin", self._data.get("SetPointOrigin",TEXT_UNKNOWN)) == "FromBoost"
            else False
        )

    @property
    def is_override(self) -> bool:
        """Get if the room has an override"""
        return (
            True
            if self._data.get("OverrideType", TEXT_UNKNOWN) != TEXT_UNKNOWN
            else False
        )

    @property
    def is_heating(self) -> bool:
        """Get if the room is currently heating"""
        return (
            True if self._data.get("ControlOutputState", TEXT_OFF) == TEXT_ON else False
        )

    @property
    def manual_target_temperature(self) -> float:
        """Get current target temperature for manual mode"""
        return _from_wiser_temp(self._data.get("ManualSetPoint", TEMP_MINIMUM))

    @property
    def mode(self) -> str:
        """Get or set current mode for the room (Off, Manual, Auto)"""
        if self._mode == WiserModeEnum.manual and self.current_target_temperature == TEMP_OFF:
            return WiserModeEnum.off.value
        return self._mode.value

    def set_mode(self, mode: str):
        if mode == WiserModeEnum.off.value:
            if self.set_manual_temperature(TEMP_OFF):
                self._mode = WiserModeEnum.off
        elif mode == WiserModeEnum.manual.value:
            if self._send_command({"Mode": WiserModeEnum.manual.value}):
                self._mode = WiserModeEnum.manual
                if self.current_target_temperature == TEMP_OFF:
                    self.override_temperature(self.scheduled_target_temperature)
        else:
            if self.is_override:
                self.cancel_overrides()
            if self._send_command({"Mode": WiserModeEnum.auto.value}):
                self._mode = WiserModeEnum.auto

    @property
    def name(self) -> str:
        """Get or set the name of the room"""
        return self._name

    def set_name(self, name: str):
        if self._send_command({"Name": name.title()}):
            self._name = name.title()

    @property
    def override_target_temperature(self) -> float:
        """Get the override target temperature of the room"""
        return self._data.get("OverrideSetpoint", 0)

    @property
    def override_type(self) -> str:
        """Get the current override type for the room"""
        return self._data.get("OverrideType", "None")

    @property
    def percentage_demand(self) -> int:
        """Get the percentage demand of the room"""
        return self._data.get("PercentageDemand", 0)

    @property
    def schedule(self):
        """Get the schedule for the room"""
        return self._schedule

    @property
    def schedule_id(self) -> int:
        """Get the schedule id for the room"""
        return self._data.get("ScheduleId")

    @property
    def scheduled_target_temperature(self) -> float:
        """Get the scheduled target temperature for the room"""
        return _from_wiser_temp(self._data.get("ScheduledSetPoint", TEMP_MINIMUM))

    @property
    def target_temperature_origin(self) -> str:
        """Get the origin of the target temperature setting for the room"""
        return self._data.get("SetpointOrigin", TEXT_UNKNOWN)

    @property
    def window_detection_active(self) -> bool:
        """Get or set if window detection is active"""
        return self._window_detection_active

    def set_window_detection_active(self, enabled: bool):
        if self._send_command({"WindowDetectionActive": enabled}):
            self._window_detection_active = enabled

    @property
    def window_state(self) -> str:
        """
        Get the currently detected window state for the room.
        Window detection needs to be active
        """
        return self._data.get("WindowState", TEXT_UNKNOWN)

    def set_boost(self, inc_temp: float, duration: int) -> bool:
        """
        Boost the temperature of the room
        param inc_temp: increase target temperature over current temperature by 0C to 5C
        param duration: the duration to boost the room temperature in minutes
        return: boolean
        """
        return self._send_command(
            {
                "RequestOverride": {
                    "Type": "Boost",
                    "DurationMinutes": duration,
                    "IncreaseSetPointBy": _to_wiser_temp(inc_temp)
                    if _to_wiser_temp(inc_temp) <= MAX_BOOST_INCREASE
                    else MAX_BOOST_INCREASE,
                }
            }
        )

    def cancel_boost(self) -> bool:
        """
        Cancel the temperature boost of the room
        return: boolean
        """
        if self.is_boosted:
            return self.cancel_overrides()
        else:
            return False

    def override_temperature(self, temp: float) -> bool:
        """
        Set the temperature of the room to override current schedule temp or in manual mode
        param temp: the temperature to set in C
        return: boolean
        """
        return self._send_command(
            {
                "RequestOverride": {
                    "Type": "Manual",
                    "SetPoint": _to_wiser_temp(temp),
                }
            }
        )

    def override_temperature_for_duration(self, temp: float, duration: int) -> bool:
        """
        Set the temperature of the room to override current schedule temp or in manual mode
        param temp: the temperature to set in C
        return: boolean
        """
        return self._send_command(
            {
                "RequestOverride": {
                    "Type": "Manual",
                    "DurationMinutes": duration,
                    "SetPoint": _to_wiser_temp(temp),
                }
            }
        )

    def set_manual_temperature(self, temp: float):
        """
        Set the manual temperature for the room
        param temp: the temperature to set in C
        return: boolean
        """
        self.set_mode(WiserModeEnum.manual.value)
        return self.override_temperature(temp)

    def schedule_advance(self):
        """
        Advance room schedule to the next scheduled time and temperature setting
        return: boolean
        """
        return self.override_temperature(
            _from_wiser_temp(self.schedule.next_entry.setting)
        )

    def cancel_overrides(self):
        """
        Cancel all overrides and set room schedule to the current temperature setting for the mode
        return: boolean
        """
        return self._send_command({"RequestOverride": {"Type": "None"}})