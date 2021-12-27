from . import _LOGGER
import enum

from .device import _WiserElectricalDevice
from .rest_controller import _WiserRestController
from .schedule import _WiserSchedule

from .const import TEXT_AUTO, TEXT_MANUAL, TEXT_ON, TEXT_OFF, TEXT_CLOSE, TEXT_NO_CHANGE, TEXT_UNKNOWN, WISERLIGHT, WISERDEVICE

import inspect

class WiserLightModeEnum(enum.Enum):
    auto = TEXT_AUTO
    manual = TEXT_MANUAL

class WiserAwayActionEnum(enum.Enum):
    off = TEXT_OFF
    nochange = TEXT_NO_CHANGE


class _WiserLight(_WiserElectricalDevice):
    """Class representing a Wiser Light device"""

    def __init__(self, wiser_rest_controller:_WiserRestController, data: dict, device_type_data: dict, schedule: _WiserSchedule):
        super().__init__(data, device_type_data)
        self._wiser_rest_controller = wiser_rest_controller
        self._device_type_data = device_type_data
        self._schedule = schedule
        self._away_action = device_type_data.get("AwayAction", TEXT_UNKNOWN)
        self._mode = device_type_data.get("Mode", TEXT_UNKNOWN)
        self._name = device_type_data.get("Name", TEXT_UNKNOWN)
        self._device_lock_enabled = data.get("DeviceLockEnabled", False)
        self._indentify_active = data.get("IdentifyActive", False)

    def _send_command(self, cmd: dict, device_level: bool = False):
        """
        Send control command to the light
        param cmd: json command structure
        return: boolen - true = success, false = failed
        """
        if device_level:
            result = self._wiser_rest_controller._send_command(WISERDEVICE.format(self.id), cmd)
        else:
            result = self._wiser_rest_controller._send_command(WISERLIGHT.format(self.id), cmd)
        if result:
            _LOGGER.debug(
                "Wiser heating actuator - {} command successful".format(
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
        return [mode.value for mode in WiserLightModeEnum]

    @property
    def available_away_mode_actions(self):
        return [action.value for action in WiserAwayActionEnum]

    @property
    def away_mode_action(self) -> str:
        """Get or set the away action of the light (off or no change)"""
        return WiserAwayActionEnum[self._away_action.lower()].value

    @away_mode_action.setter
    def away_mode_action(self, action: str):
        if self._validate_away_action(action):
            if self._send_command({"AwayAction": WiserAwayActionEnum[action.lower()].value}):
                self._away_action = WiserAwayActionEnum[action.lower()].value
        else:
            raise ValueError(f"{action} is not a valid Light away mode action.  Valid modes are {self.available_away_mode_actions}")

    @property
    def control_source(self) -> str:
        """Get the current control source of the shutter"""
        return self._device_type_data.get("ControlSource", TEXT_UNKNOWN)

    @property
    def current_level(self) -> int:
        """Get amount light is on"""
        return self._device_type_data.get("CurrentLevel", 0)

    @property
    def current_percentage(self) -> int:
        """Get percentage amount light is on"""
        return self._device_type_data.get("CurrentPercentage", 0)

    @property
    def current_state(self) -> str:
        """Get if light is on"""
        return self._device_type_data.get("CurrentState", 0)

    @property
    def identify(self) -> bool:
        """Get or set if the light identify function is enabled"""
        return self._indentify_active

    @identify.setter
    def identify(self, enable: bool = False):
        if self._send_command({"Identify": enable}, True):
            self._indentify_active = enable

    @property
    def mode(self) -> str:
        """Get or set the current mode of the light (Manual or Auto)"""
        return WiserLightModeEnum[self._mode.lower()].value

    @mode.setter
    def mode(self, mode: str):
        if self._validate_mode(mode):
            if self._send_command({"Mode": WiserLightModeEnum[mode.lower()].value}):
                self._mode = WiserLightModeEnum[mode.lower()].value
        else:
            raise ValueError(f"{mode} is not a valid Light mode.  Valid modes are {self.available_modes}")

    @property
    def name(self) -> str:
        """Get or set the name of the light"""
        return self._name

    @name.setter
    def name(self, name: str):
        if self._send_command({"Name": name}):
            self._name = name

    @property
    def is_dimmable(self) -> bool:
        """Get if the light is dimmable"""
        return True if self._device_type_data.get("IsDimmable", False) else False

    @property
    def is_on(self) -> bool:
        """Get if the light is on"""
        return True if self._device_type_data.get("CurrentState", TEXT_OFF) == TEXT_ON else False

    @property
    def light_id(self) -> int:
        """Get id of light"""
        return self._device_type_data.get("id", 0)

    @property
    def room_id(self) -> int:
        """Get smart plug room id"""
        return self._device_type_data.get("RoomId", 0)

    @property
    def schedule(self):
        """Get the schedule of the smart plug"""
        return self._schedule
      

class _WiserLightCollection(object):
    """Class holding all wiser lights"""

    def __init__(self):
        self._lights = []

    @property
    def all(self) -> dict:
        return list(self._lights)

    @property
    def count(self) -> int:
        return len(self.all)

    def get_by_id(self, id: int) -> _WiserLight:
        """
        Gets a Light object from the Lights device id
        param id: device id of shutter
        return: _WiserShutter object
        """
        try:
            return [
                light for light in self.all if light.id == id
            ][0]
        except IndexError:
            return None

    def get_by_light_id(self, light_id: int) -> _WiserLight:
        """
        Gets a Light object from the Lights id
        param id: id of light
        return: _WiserLight object
        """
        try:
            return [
                light for light in self.all if light.light_id == light_id
            ][0]
        except IndexError:
            return None
    
    def get_by_room_id(self, room_id: int) -> list:
        """
        Gets a Light object from the Lights room_id
        param id: room_id of light
        return: list of _WiserLight objects
        """
        return [
            light for light in self.all if light.room_id == room_id
        ]
