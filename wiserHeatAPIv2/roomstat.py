from . import _LOGGER

from .device import _WiserDevice
from .helpers import _WiserBattery
from .helpers import _WiserTemperatureFunctions as tf
from .rest_controller import _WiserRestController

from .const import (
    WISERROOMSTAT,
    WISERDEVICE
)

import inspect

class _WiserRoomStat(_WiserDevice):
    """Class representing a Wiser Room Stat device"""

    def __init__(self, wiser_rest_controller:_WiserRestController, data, device_type_data):
        super().__init__(data)
        self._wiser_rest_controller = wiser_rest_controller
        self._device_type_data = device_type_data
        self._device_lock_enabled = data.get("DeviceLockEnabled", False)
        self._indentify_active = data.get("IdentifyActive", False)

    def _send_command(self, cmd: dict, device_level: bool = False) -> bool:
        """
        Send control command to the room stat
        param cmd: json command structure
        return: boolen - true = success, false = failed
        """
        if device_level:
            result = self._wiser_rest_controller._send_command(WISERDEVICE.format(self.id), cmd)
        else:
            result = self._wiser_rest_controller._send_command(WISERROOMSTAT.format(self.id), cmd)
        if result:
            _LOGGER.debug(
                "Wiser room stat - {} command successful".format(
                    inspect.stack()[1].function
                )
            )
        return result

    @property
    def battery(self) -> _WiserBattery:
        """Get the battery information for the room stat"""
        return _WiserBattery(self._data)

    @property
    def current_humidity(self) -> int:
        """Get the current humidity reading of the room stat"""
        return self._device_type_data.get("MeasuredHumidity", 0)

    @property
    def current_target_temperature(self) -> float:
        """Get the room stat current target temperature setting"""
        return tf._from_wiser_temp(self._device_type_data.get("SetPoint", 0))

    @property
    def current_temperature(self) -> float:
        """Get the current temperature measured by the room stat"""
        return tf._from_wiser_temp(self._device_type_data.get("MeasuredTemperature", 0), "current")

    @property
    def device_lock_enabled(self) -> bool:
        """Get or set room stat device lock"""
        return self._device_lock_enabled

    @device_lock_enabled.setter
    def device_lock_enabled(self, enable: bool):
        """
        Set the device lock setting on the room stat
        param enabled: turn on or off
        """
        return self._send_command({"DeviceLockEnabled": enable}, True)

    @property
    def identify(self) -> bool:
        """Get or set if the room stat identify function is enabled"""
        return self._indentify_active

    @identify.setter
    def identify(self, enable: bool = False):
        """
        Set the identify function setting on the room stat
        param enabled: turn on or off
        """
        if self._send_command({"Identify": enable}, True):
            self._indentify_active = enable

    @property
    def room_id(self) -> int:
        """Get roomstat room id"""
        return self._device_type_data.get("RoomId", 0)


class _WiserRoomStatCollection(object):
    """Class holding all wiser room stats"""

    def __init__(self):
        self._roomstats = []

    @property
    def all(self) -> list:
        return list(self._roomstats)

    @property
    def count(self) -> int:
        return len(self.all)

    # Roomstats
    def get_by_id(self, id: int) -> _WiserRoomStat:
        """
        Gets a RoomStat object from the RoomStats id
        param id: id of room stat
        return: _WiserRoomStat object
        """
        for roomstat in self.all:
            if roomstat.id == id:
                return roomstat
        return None