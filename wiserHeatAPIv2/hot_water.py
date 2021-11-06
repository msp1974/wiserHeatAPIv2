import inspect
import logging
from .rest_controller import _WiserRestController
from .const import (
    HW_ON,
    HW_OFF,
    TEXT_ON,
    TEXT_UNKNOWN, 
    WISERHOTWATER,
    WiserModeEnum,
    WiserHotWaterStateEnum
)
from .helpers import (
    _to_wiser_temp
)

_LOGGER = logging.getLogger(__name__)

class _WiserHotwater:
    """Class representing a Wiser Hot Water controller"""

    def __init__(self, data: dict, schedule: dict):
        self._data = data
        self._schedule = schedule
        self._mode = data.get("Mode")

    def _send_command(self, cmd: dict):
        """
        Send control command to the hot water
        param cmd: json command structure
        return: boolen - true = success, false = failed
        """
        rest = _WiserRestController()
        result = rest._send_command(WISERHOTWATER.format(self.id), cmd)
        if result:
            _LOGGER.info(
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
    def is_heating(self) -> bool:
        """Get if the hot water is currently heating"""
        return True if self._data.get("WaterHeatingState") == TEXT_ON else False

    @property
    def is_boosted(self) -> bool:
        """Get if the hot water is currently boosted"""
        return True if self._data.get("Override") else False  # TODO: Check this

    @property
    def mode(self) -> str:
        """Get or set the current hot water mode (Manual or Auto)"""
        return self._mode

    @mode.setter
    def mode(self, mode: WiserModeEnum):
        if mode == WiserModeEnum.off:
            if self._send_command({"Mode": WiserModeEnum.manual.value}):
                self.override_state(WiserHotWaterStateEnum.off)
        else:
            if self._send_command({"Mode": mode.value}):
                self._mode = mode.value

    @property
    def schedule(self):
        """Get the hot water schedule"""
        return self._schedule

    def schedule_advance(self):
        """
        Advance hot water schedule to the next scheduled time and state setting
        return: boolean
        """
        # TODO: Fix this!
        if self.schedule.next_entry.setting == WiserHotWaterStateEnum.on.value:
            return self.override_state(WiserHotWaterStateEnum.on)
        else:
            return self.override_state(WiserHotWaterStateEnum.off)

    def override_state(self, state: WiserHotWaterStateEnum) -> bool:
        """
        Override hotwater state.  In auto this is until the next scheduled event.  In manual mode this is until changed.
        return: boolean
        """
        if state == WiserHotWaterStateEnum.on:
            return self._send_command(
                {"RequestOverride": {"Type": "Manual", "SetPoint": _to_wiser_temp(HW_ON)}}
            )
        else:
            return self._send_command(
                {"RequestOverride": {"Type": "Manual", "SetPoint": _to_wiser_temp(HW_OFF)}}
            )

    def override_state_for_duration(self, state: WiserHotWaterStateEnum, duration: int) -> bool:
        """
        Override the hot water state for x minutes, overriding the current schedule or manual setting
        param duration: the duration to turn on for in minutes
        return: boolean
        """
        if state == WiserHotWaterStateEnum.on:
            return self._send_command(
                {
                    "RequestOverride": {
                        "Type": "Manual",
                        "DurationMinutes": duration,
                        "SetPoint": _to_wiser_temp(HW_ON)
                    }
                }
            )
        else:
            return self._send_command(
                {
                    "RequestOverride": {
                        "Type": "Manual",
                        "DurationMinutes": duration,
                        "SetPoint": _to_wiser_temp(HW_OFF)
                    }
                }
            )

    def cancel_overrides(self):
        """
        Cancel all overrides of the hot water
        return: boolean
        """
        return self._send_command({"RequestOverride": {"Type": "None"}})