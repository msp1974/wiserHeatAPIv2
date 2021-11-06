
from .device import _WiserDevice, _WiserBattery
from .helpers import _to_wiser_temp, _from_wiser_temp
from .rest_controller import _WiserRestController
from .schedule import _WiserSchedule
from .const import (
    WISERSMARTPLUG,
    TEXT_UNKNOWN,
    TEXT_OFF,
    TEXT_ON,
    WiserAwayActionEnum,
    WiserModeEnum
)

import inspect
import logging

_LOGGER = logging.getLogger(__name__)

class _WiserSmartPlug(_WiserDevice):
    """Class representing a Wiser Smart Plug device"""

    def __init__(self, data: dict, device_type_data: dict, schedule: _WiserSchedule):
        super().__init__(data)
        self._data = data
        self._device_type_data = device_type_data
        self._schedule = schedule

        self._away_action = device_type_data.get("AwayAction", TEXT_UNKNOWN)
        self._mode = device_type_data.get("Mode", TEXT_UNKNOWN)
        self._name = device_type_data.get("Name", TEXT_UNKNOWN)
        self._output_state = device_type_data.get("OutputState", TEXT_OFF)

    def _send_command(self, cmd: dict):
        """
        Send control command to the smart plug
        param cmd: json command structure
        return: boolen - true = success, false = failed
        """
        rest = _WiserRestController()
        result = rest._send_command(WISERSMARTPLUG.format(self.id), cmd)
        if result:
            _LOGGER.info(
                "Wiser smart plug - {} command successful".format(
                    inspect.stack()[1].function
                )
            )
        return result

    @property
    def away_action(self) -> str:
        """Get or set the away action of the smart plug (off or no change)"""
        return self._away_action

    @away_action.setter
    def away_action(self, action: WiserAwayActionEnum):
        result = self._send_command({"AwayAction": action.value})
        if result:
            self._away_action = action.value

    @property
    def control_source(self) -> str:
        """Get the current control source of the smart plug"""
        return self._device_type_data.get("ControlSource", TEXT_UNKNOWN)

    @property
    def manual_state(self) -> str:
        """Get the current manual mode setting of the smart plug"""
        return self._device_type_data.get("ManualState", TEXT_UNKNOWN)

    @property
    def mode(self) -> str:
        """Get or set the current mode of the smart plug (Manual or Auto)"""
        return self._mode

    @mode.setter
    def mode(self, mode: WiserModeEnum):
        if mode == WiserModeEnum.off:
            raise ValueError("You cannot set a smart plug to off mode.")
        else:
            if self._send_command({"Mode": mode.value}):
                self._mode = mode

    @property
    def name(self) -> str:
        """Get or set the name of the smart plug"""
        return self._name

    @name.setter
    def name(self, name: str):
        if self._send_command({"Name": name}):
            self._name = name

    @property
    def is_on(self) -> bool:
        """Get if the smart plug is on"""
        return True if self._output_state == TEXT_ON else False

    @property
    def room_id(self) -> int:
        """Get smart plug room id"""
        return self._device_type_data.get("RoomId", 0)

    @property
    def schedule(self):
        """Get the schedule of the smart plug"""
        return self._schedule

    @property
    def scheduled_state(self) -> str:
        """Get the current scheduled state of the smart plug"""
        return self._device_type_data.get("ScheduledState", TEXT_UNKNOWN)

    def turn_on(self) -> bool:
        """
        Turn on the smart plug
        return: boolean
        """
        result = self._send_command({"RequestOutput": TEXT_ON})
        if result:
            self._output_is_on = True
        return result

    def turn_off(self) -> bool:
        """
        Turn off the smart plug
        return: boolean
        """
        result = self._send_command({"RequestOutput": TEXT_OFF})
        if result:
            self._output_is_on = False
        return result