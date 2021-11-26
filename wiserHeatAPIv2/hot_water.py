from . import _LOGGER

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
    WiserHotWaterModeEnum,
)

import inspect


class _WiserHotwater(object):
    """Class representing a Wiser Hot Water controller"""

    def __init__(self, wiser_rest_controller:_WiserRestController, hw_data: dict, schedule: dict):
        self._wiser_rest_controller = wiser_rest_controller
        self._data = hw_data
        self._schedule = schedule
        self._mode = self._effective_hotwater_mode(self._data.get("Mode",{}), self.current_state)

    def _effective_hotwater_mode(self, mode: str, state: str) -> WiserHotWaterModeEnum:
        if mode == TEXT_MANUAL and state == TEXT_OFF:
            return WiserHotWaterModeEnum.off
        if mode == TEXT_MANUAL and state == TEXT_ON:
            return WiserHotWaterModeEnum.on
        return WiserHotWaterModeEnum.auto

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
        return True if self._data.get("OverrideTimeoutUnixTime", None) else False

    @property
    def is_heating(self) -> bool:
        """Get if the hot water is currently heating"""
        return True if self._data.get("WaterHeatingState") == TEXT_ON else False

    @property
    def mode(self) -> WiserHotWaterModeEnum:
        """Get or set the current hot water mode (Manual or Auto)"""
        return self._mode

    @mode.setter
    def mode(self, mode: WiserHotWaterModeEnum):
        if mode == WiserHotWaterModeEnum.off:
            if self._send_command({"Mode": TEXT_MANUAL}):
                self.override_state(WiserHotWaterModeEnum.off)
        elif mode == WiserHotWaterModeEnum.on:
            if self._send_command({"Mode": TEXT_MANUAL}):
                self.override_state(WiserHotWaterModeEnum.on)
        elif mode == WiserHotWaterModeEnum.auto:
            if self._send_command({"Mode": TEXT_AUTO}):
                self.cancel_overrides()
        self._mode = mode

    @property
    def schedule(self) -> _WiserSchedule:
        """Get the hot water schedule"""
        return self._schedule

    def schedule_advance(self):
        """
        Advance hot water schedule to the next scheduled time and state setting
        return: boolean
        """
        if self.schedule.next_entry.setting == WiserHotWaterModeEnum.on.value:
            return self.override_state(WiserHotWaterModeEnum.on)
        else:
            return self.override_state(WiserHotWaterModeEnum.off)

    def override_state(self, state: WiserHotWaterModeEnum) -> bool:
        """
        Override hotwater state.  In auto this is until the next scheduled event.  In manual mode this is until changed.
        return: boolean
        """
        if state == WiserHotWaterModeEnum.on:
            return self._send_command(
                {"RequestOverride": {"Type": "Manual", "SetPoint": TEMP_HW_ON * 10}}
            )
        else:
            return self._send_command(
                {"RequestOverride": {"Type": "Manual", "SetPoint": TEMP_HW_OFF * 10}}
            )

    def boost(self, duration: int) -> bool:
        """
        Turn the hot water on for x minutes, overriding the current schedule or manual setting
        param duration: the duration to turn on for in minutes
        return: boolean
        """
        return self.override_state_for_duration(WiserHotWaterModeEnum.on, duration)

    def override_state_for_duration(self, state: WiserHotWaterModeEnum, duration: int) -> bool:
        """
        Override the hot water state for x minutes, overriding the current schedule or manual setting
        param duration: the duration to turn on for in minutes
        return: boolean
        """
        if state == WiserHotWaterModeEnum.on:
            return self._send_command(
                {
                    "RequestOverride": {
                        "Type": "Manual",
                        "DurationMinutes": duration,
                        "SetPoint": tf._to_wiser_temp(TEMP_HW_ON)
                    }
                }
            )
        else:
            return self._send_command(
                {
                    "RequestOverride": {
                        "Type": "Manual",
                        "DurationMinutes": duration,
                        "SetPoint": tf._to_wiser_temp(TEMP_HW_OFF)
                    }
                }
            )

    def cancel_overrides(self):
        """
        Cancel all overrides of the hot water
        return: boolean
        """
        return self._send_command({"RequestOverride": {"Type": "None"}})