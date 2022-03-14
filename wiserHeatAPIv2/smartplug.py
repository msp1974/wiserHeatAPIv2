from . import _LOGGER
import enum

from .device import _WiserDevice
from .rest_controller import _WiserRestController
from .schedule import _WiserSchedule

from .const import (
    WISERSMARTPLUG,
    WISERDEVICE,
    TEXT_UNKNOWN,
    TEXT_AUTO,
    TEXT_MANUAL,
    TEXT_OFF,
    TEXT_ON,
    TEXT_NO_CHANGE
)

class WiserSmartPlugModeEnum(enum.Enum):
    auto = TEXT_AUTO
    manual = TEXT_MANUAL

class WiserAwayActionEnum(enum.Enum):
    off = TEXT_OFF
    nochange = TEXT_NO_CHANGE


import inspect


class _WiserSmartPlug(_WiserDevice):
    """Class representing a Wiser Smart Plug device"""
    
    def __init__(self, wiser_rest_controller:_WiserRestController, data: dict, device_type_data: dict, schedule: _WiserSchedule):
        super().__init__(data)
        self._wiser_rest_controller = wiser_rest_controller
        self._device_type_data = device_type_data
        self._schedule = schedule
        self._away_action = device_type_data.get("AwayAction", TEXT_UNKNOWN)
        self._mode = device_type_data.get("Mode", TEXT_UNKNOWN)
        self._name = device_type_data.get("Name", TEXT_UNKNOWN)
        self._device_lock_enabled = data.get("DeviceLockEnabled", False)
        self._output_state = device_type_data.get("OutputState", TEXT_OFF)

    def _send_command(self, cmd: dict, device_level: bool = False):
        """
        Send control command to the smart plug
        param cmd: json command structure
        return: boolen - true = success, false = failed
        """
        if device_level:
            result = self._wiser_rest_controller._send_command(WISERDEVICE.format(self.id), cmd)
        else:
            result = self._wiser_rest_controller._send_command(WISERSMARTPLUG.format(self.id), cmd)
        if result:
            _LOGGER.debug(
                "Wiser smart plug - {} command successful".format(
                    inspect.stack()[1].function
                )
            )
        return result

    def _validate_mode(self, mode: str) -> bool:
        for available_mode in self.available_modes:
            if mode.casefold() == available_mode.casefold():
                return True
        return False

    def _validate_away_action(self, action: str) -> bool:
        for action in self.available_away_mode_actions:
            if action.casefold() == action.casefold():
                return True
        return False

    @property
    def available_modes(self):
        return [mode.value for mode in WiserSmartPlugModeEnum]

    @property
    def available_away_mode_actions(self):
        return [action.value for action in WiserAwayActionEnum]

    @property
    def away_mode_action(self) -> str:
        """Get or set the away action of the smart plug (off or no change)"""
        return WiserAwayActionEnum[self._away_action.lower()].value

    @away_mode_action.setter
    def away_mode_action(self, action: str):
        if self._validate_away_action(action):
            if self._send_command({"AwayAction": WiserAwayActionEnum[action.lower()].value}):
                self._away_action = WiserAwayActionEnum[action.lower()].value
        else:
            raise ValueError(f"{action} is not a valid Smart Plug away mode action.  Valid modes are {self.available_away_mode_actions}")

    @property
    def control_source(self) -> str:
        """Get the current control source of the smart plug"""
        return self._device_type_data.get("ControlSource", TEXT_UNKNOWN)

    @property
    def delivered_power(self) -> int:
        """Get the amount of current throught the plug over time"""
        return self._device_type_data.get("CurrentSummationDelivered", -1)

    @property
    def device_lock_enabled(self) -> bool:
        """Get or set smart plug device lock"""
        return self._device_lock_enabled

    @device_lock_enabled.setter
    def device_lock_enabled(self, enable: bool):
        if self._send_command({"DeviceLockEnabled": enable}, True):
            self._device_lock_enabled = enable

    @property
    def instantaneous_power(self) -> int:
        """Get the amount of current throught the plug now"""
        return self._device_type_data.get("InstantaneousDemand", -1)

    @property
    def manual_state(self) -> str:
        """Get the current manual mode setting of the smart plug"""
        return self._device_type_data.get("ManualState", TEXT_UNKNOWN)

    @property
    def mode(self) -> str:
        """Get or set the current mode of the smart plug (Manual or Auto)"""
        return WiserSmartPlugModeEnum[self._mode.lower()].value

    @mode.setter
    def mode(self, mode: str):
        if self._validate_mode(mode):
            if self._send_command({"Mode": WiserSmartPlugModeEnum[mode.lower()].value}):
                self._mode = WiserSmartPlugModeEnum[mode.lower()].value
        else:
            raise ValueError(f"{mode} is not a valid Smart Plug mode.  Valid modes are {self.available_modes}")

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
    def schedule_id(self):
        """Get the schedule_id of the smart plug"""
        return self._device_type_data.get("ScheduleId", 0)

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
            self._output_state = TEXT_ON
        return result

    def turn_off(self) -> bool:
        """
        Turn off the smart plug
        return: boolean
        """
        result = self._send_command({"RequestOutput": TEXT_OFF})
        if result:
            self._output_state = TEXT_OFF
        return result


class _WiserSmartPlugCollection(object):
    """Class holding all wiser smart plugs"""

    def __init__(self):
        self._smartplugs = []

    @property
    def all(self) -> dict:
        return list(self._smartplugs)

    @property
    def available_modes(self):
        return [mode.value for mode in WiserSmartPlugModeEnum]

    @property
    def count(self) -> int:
        return len(self.all)

    # Smartplugs
    def get_by_id(self, id: int) -> _WiserSmartPlug:
        """
        Gets a SmartPlug object from the SmartPlugs id
        param id: id of smart plug
        return: _WiserSmartPlug object
        """
        try:
            return [smartplug for smartplug in self.all if smartplug.id == id][0]
        except IndexError:
            return None


