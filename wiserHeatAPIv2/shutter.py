from . import _LOGGER
import enum

from .device import _WiserElectricalDevice
from .helpers import _WiserTemperatureFunctions as tf
from .rest_controller import _WiserRestController
from .schedule import _WiserSchedule

from .const import TEXT_AUTO, TEXT_MANUAL, TEXT_OPEN, TEXT_CLOSE, TEXT_NO_CHANGE, TEXT_UNKNOWN, WISERSHUTTER, WISERDEVICE

import inspect

class WiserShutterModeEnum(enum.Enum):
    auto = TEXT_AUTO
    manual = TEXT_MANUAL

class WiserAwayActionEnum(enum.Enum):
    close = TEXT_CLOSE
    nochange = TEXT_NO_CHANGE


class _WiserShutter(_WiserElectricalDevice):
    """Class representing a Wiser Shutter device"""

    class _WiserLiftMovementRange(object):
        """ Data structure for min/max output range"""
        def __init__(self, shutter_instance, data: dict):
            self._shutter_instance = shutter_instance
            self._data = data

        @property
        def open_time(self) -> int:
            """Get open time value"""
            if self._data:
                return self._data.get("LiftOpenTime")
            return None

        @open_time.setter
        def open_time(self, time: int):
            """Set open time"""
            return self._shutter_instance._send_command({"LiftOpenTime": time, "LiftCloseTime": self.close_time})

        @property
        def close_time(self) -> int:
            """Get close time value"""
            if self._data:
                return self._data.get("LiftCloseTime")
            return None

        @close_time.setter
        def close_time(self, time: int):
            """Set close time"""
            return self._shutter_instance._send_command({"LiftOpenTime": self.open_time, "LiftCloseTime": time})


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
        Send control command to the shutter
        param cmd: json command structure
        return: boolen - true = success, false = failed
        """
        if device_level:
            result = self._wiser_rest_controller._send_command(WISERDEVICE.format(self.shutter_id), cmd)
        else:
            result = self._wiser_rest_controller._send_command(WISERSHUTTER.format(self.shutter_id), cmd)
        if result:
            _LOGGER.debug(
                "Wiser shutter - {} command successful".format(
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
        return [mode.value for mode in WiserShutterModeEnum]

    @property
    def available_away_mode_actions(self):
        return [action.value for action in WiserAwayActionEnum]

    @property
    def away_mode_action(self) -> str:
        """Get or set the away action of the shutter (close or no change)"""
        return WiserAwayActionEnum[self._away_action.lower()].value

    @away_mode_action.setter
    def away_mode_action(self, action: str):
        if self._validate_away_action(action):
            if self._send_command({"AwayAction": WiserAwayActionEnum[action.lower()].value}):
                self._away_action = WiserAwayActionEnum[action.lower()].value
        else:
            raise ValueError(f"{action} is not a valid Shutter away mode action.  Valid modes are {self.available_away_mode_actions}")

    @property
    def control_source(self) -> str:
        """Get the current control source of the shutter"""
        return self._device_type_data.get("ControlSource", TEXT_UNKNOWN)

    @property
    def current_lift(self) -> bool:
        """Get amount shutter is open"""
        return self._device_type_data.get("CurrentLift", 0)

    @current_lift.setter
    def current_lift(self, percentage: int):
        """ Open shutter to defined level """
        if percentage >= 0 and percentage <= 100:
            self._send_command({"RequestAction":{"Action": "LiftTo", "Percentage": percentage}})
        else:
            raise ValueError(f"Shutter percentage must be between 0 and 100")

    @property
    def drive_config(self) -> _WiserLiftMovementRange:
        """Get open and close time drive config"""
        return self._WiserLiftMovementRange(self, self._device_type_data.get("DriveConfig"))

    @property
    def identify(self) -> bool:
        """Get or set if the shutter identify function is enabled"""
        return self._indentify_active

    @identify.setter
    def identify(self, enable: bool = False):
        if self._send_command({"Identify": enable}, True):
            self._indentify_active = enable

    @property
    def is_open(self) -> bool:
        """Get if the shutter is open"""
        return True if self._device_type_data.get("CurrentLift", 0) == 100 else False

    @property
    def is_closed(self) -> bool:
        """Get if the shutter is closed"""
        return True if self._device_type_data.get("CurrentLift", 0) == 0 else False

    @property
    def is_closing(self) -> bool:
        """Get if shutter is moving-opening"""
        return True if self._device_type_data.get("LiftMovement", TEXT_UNKNOWN) == 'Closing' else False

    @property
    def is_opening(self) -> bool:
        """Get if shutter is moving-opening"""
        return True if self._device_type_data.get("LiftMovement", TEXT_UNKNOWN) == 'Opening' else False

    @property
    def is_stopped(self) -> bool:
        """Get if shutter is not moving"""
        return True if self._device_type_data.get("LiftMovement", TEXT_UNKNOWN) == 'Stopped' else False

    @property
    def is_moving(self) -> bool:
        """Get if shutter is moving"""
        return True if self._device_type_data.get("LiftMovement", TEXT_UNKNOWN) != 'Stopped' else False

    @property
    def lift_movement(self) -> str:
        """Get if shutter is moving"""
        return self._device_type_data.get("LiftMovement", TEXT_UNKNOWN)
    
    @property
    def manual_lift(self) -> int:
        """Get shutter manual lift value"""
        return self._device_type_data.get("ManualLift", 0)

    @property
    def mode(self) -> str:
        """Get or set the current mode of the shutter (Manual or Auto)"""
        return WiserShutterModeEnum[self._mode.lower()].value

    @mode.setter
    def mode(self, mode: str):
        if self._validate_mode(mode):
            if self._send_command({"Mode": WiserShutterModeEnum[mode.lower()].value}):
                self._mode = WiserShutterModeEnum[mode.lower()].value
        else:
            raise ValueError(f"{mode} is not a valid Shutter mode.  Valid modes are {self.available_modes}")

    @property
    def name(self) -> str:
        """Get or set the name of the shutter"""
        return self._name

    @name.setter
    def name(self, name: str):
        if self._send_command({"Name": name}):
            self._name = name

    @property
    def room_id(self) -> int:
        """Get smart plug room id"""
        return self._device_type_data.get("RoomId", 0)

    @property
    def schedule(self):
        """Get the schedule of the shutter"""
        return self._schedule

    @property
    def schedule_id(self) -> int:
        """Get the schedule id for the room"""
        return self._device_type_data.get("ScheduleId")

    @property
    def scheduled_lift(self) -> str:
        """Get the current scheduled lift of the shutter"""
        return self._device_type_data.get("ScheduledLift", TEXT_UNKNOWN)

    @property
    def shutter_id(self) -> int:
        """Get id of shutter"""
        return self._device_type_data.get("id", 0)

    @property
    def target_lift(self) -> int:
        """Get target position of shutter"""
        return self._device_type_data.get("TargetLift", 0)

    def open(self):
        """ Fully open shutter """
        self._send_command({"RequestAction":{"Action": "LiftTo", "Percentage": 100}})

    def close(self):
        """ Fully close shutter """
        self._send_command({"RequestAction":{"Action": "LiftTo", "Percentage": 0}})

    def stop(self):
        """ Stop shutter during movement """
        self._send_command({"RequestAction":{"Action": "Stop"}})



class _WiserShutterCollection(object):
    """Class holding all wiser heating actuators"""

    def __init__(self):
        self._shutters = []

    @property
    def all(self) -> dict:
        return list(self._shutters)

    @property
    def available_modes(self):
        return [mode.value for mode in WiserShutterModeEnum]

    @property
    def count(self) -> int:
        return len(self.all)

    def get_by_id(self, id: int) -> _WiserShutter:
        """
        Gets a Shutter object from the Shutters device id
        param id: device id of shutter
        return: _WiserShutter object
        """
        try:
            return [
                shutter for shutter in self.all if shutter.id == id
            ][0]
        except IndexError:
            return None

    def get_by_shutter_id(self, shutter_id: int) -> _WiserShutter:
        """
        Gets a Shutter object from the Shutters id
        param id: id of shutter
        return: _WiserShutter object
        """
        try:
            return [
                shutter for shutter in self.all if shutter.shutter_id == shutter_id
            ][0]
        except IndexError:
            return None
    
    def get_by_room_id(self, room_id: int) -> list:
        """
        Gets a Shutter object from the Shutters room_id
        param id: room_id of shutter
        return: list of _WiserShutter objects
        """
        return [
            shutter for shutter in self.all if shutter.room_id == room_id
        ]
