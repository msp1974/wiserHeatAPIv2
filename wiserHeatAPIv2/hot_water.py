from . import _LOGGER
import enum
from datetime import datetime
from .helpers import _WiserTemperatureFunctions as tf
from .rest_controller import _WiserRestController
from .schedule import _WiserSchedule

from .const import (
    TEMP_HW_ON,
    TEMP_HW_OFF,
    TEXT_AUTO,
    TEXT_MANUAL,
    TEXT_OFF,
    TEXT_ON,
    TEXT_UNKNOWN, 
    WISERHOTWATER,
)

class WiserHotWaterModeEnum(enum.Enum):
    auto = TEXT_AUTO
    manual = TEXT_MANUAL

import inspect


class _WiserHotwater(object):
    """Class representing a Wiser Hot Water controller"""

    def __init__(self, wiser_rest_controller:_WiserRestController, hw_data: dict, schedule: dict):
        self._wiser_rest_controller = wiser_rest_controller
        self._data = hw_data
        self._schedule = schedule
        self._mode = self._data.get("Mode", TEXT_AUTO)

    def _send_command(self, cmd: dict):
        """
        Send control command to the hot water
        param cmd: json command structure
        return: boolen - true = success, false = failed
        """
        result = self._wiser_rest_controller._send_command(WISERHOTWATER.format(self.id), cmd)
        if result:
            _LOGGER.debug(
                "Wiser hot water - {} command successful".format(
                    inspect.stack()[1].function
                )
            )
        return result

    def _validate_mode(self, mode: str) -> bool:
        for available_mode in self.available_modes:
            if mode.casefold() == available_mode.casefold():
                return True
        return False

    @property
    def available_modes(self) -> str:
         return [mode.value for mode in WiserHotWaterModeEnum]

    @property
    def away_mode_suppressed(self):
        """Get if away mode is suppressed for room"""
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
    def current_control_source(self) -> str:
        """Get the current control source for the hot water"""
        return self._data.get("HotWaterDescription", TEXT_UNKNOWN)

    @property
    def current_state(self) -> str:
        """Get the current state of the hot water"""
        return self._data.get("HotWaterRelayState", TEXT_UNKNOWN)

    @property
    def id(self) -> int:
        """Get the id of the hot water channel"""
        return self._data.get("id")

    @property
    def is_away_mode(self) -> bool:
        return True if self._data.get("HotWaterDescription") == "FromAwayMode" else False

    @property
    def is_boosted(self) -> bool:
        """Get if the hot water is currently boosted"""
        return True if "Boost" in self._data.get("HotWaterDescription", None) else False

    @property
    def is_heating(self) -> bool:
        """Get if the hot water is currently heating"""
        return True if self._data.get("WaterHeatingState") == TEXT_ON else False

    @property
    def is_override(self) -> bool:
        """Get if the room has an override"""
        return (
            True
            if self._data.get("OverrideType", TEXT_UNKNOWN) not in  [TEXT_UNKNOWN, "None"]
            else False
        )

    @property
    def mode(self) -> str:
        """Get or set the current hot water mode (On, Off or Auto)"""
        try:
            return WiserHotWaterModeEnum[self._mode.lower()].value
        except KeyError:
            return None

    @mode.setter
    def mode(self, mode: str):
        if self._validate_mode(mode):
                self._send_command({"Mode": mode})
        else:
            raise ValueError(
                f"{mode} is not a valid Hot Water mode.  Valid modes are {self.available_modes}"
            )
        self._mode = WiserHotWaterModeEnum[mode.lower()].value

    @property
    def schedule(self) -> _WiserSchedule:
        """Get the hot water schedule"""
        return self._schedule

    @property
    def schedule_id(self):
        """Get the hot water schedule id"""
        return self._data.get("ScheduleId", 0)

    def boost(self, duration: int) -> bool:
        """
        Turn the hot water on for x minutes, overriding the current schedule or manual setting
        param duration: the duration to turn on for in minutes
        return: boolean
        """
        return self.override_state_for_duration(TEXT_ON, duration)

    def cancel_boost(self) -> bool:
        """
        Cancel the target temperature boost of the room
        return: boolean
        """
        if self.is_boosted:
            return self.cancel_overrides()
        else:
            return True

    def cancel_overrides(self):
        """
        Cancel all overrides of the hot water
        return: boolean
        """
        return self._send_command({"RequestOverride": {"Type": "None"}})

    def override_state(self, state: str) -> bool:
        """
        Override hotwater state.  In auto this is until the next scheduled event.  In manual mode this is until changed.
        return: boolean
        """
        if self.cancel_boost():
            if state.casefold() == TEXT_ON.casefold():
                return self._send_command(
                    {"RequestOverride": {"Type": "Manual", "SetPoint": tf._to_wiser_temp(TEMP_HW_ON, "hotwater")}}
                )
            elif state.casefold() == TEXT_OFF.casefold():
                return self._send_command(
                    {"RequestOverride": {"Type": "Manual", "SetPoint": tf._to_wiser_temp(TEMP_HW_OFF, "hotwater")}}
                )
            else:
                raise ValueError(
                    f"Invalid state value {state}.  Should be {TEXT_ON} or {TEXT_OFF}"
                )

    def override_state_for_duration(self, state: str, duration: int) -> bool:
        """
        Override the hot water state for x minutes, overriding the current schedule or manual setting
        param duration: the duration to turn on for in minutes
        return: boolean
        """
        if state.casefold() == TEXT_ON.casefold():
            return self._send_command(
                {
                    "RequestOverride": {
                        "Type": "Manual",
                        "DurationMinutes": duration,
                        "SetPoint": tf._to_wiser_temp(TEMP_HW_ON, "hotwater")
                    }
                }
            )
        elif state.casefold() == TEXT_OFF.casefold():
            return self._send_command(
                {
                    "RequestOverride": {
                        "Type": "Manual",
                        "DurationMinutes": duration,
                        "SetPoint": tf._to_wiser_temp(TEMP_HW_OFF)
                    }
                }
            )
        else:
            raise ValueError(
                f"Invalid state value {state}.  Should be {TEXT_ON} or {TEXT_OFF}"
            )

    def schedule_advance(self):
        """
        Advance hot water schedule to the next scheduled state setting
        return: boolean
        """
        if self.schedule:
            if self.cancel_boost():
                return self.override_state(self.schedule.next.setting)
        return False
