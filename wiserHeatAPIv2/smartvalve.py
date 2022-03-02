from . import _LOGGER

from .device import _WiserDevice
from .helpers import _WiserTemperatureFunctions as tf, _WiserBattery
from .rest_controller import _WiserRestController

from .const import WISERSMARTVALVE, WISERDEVICE

import inspect


class _WiserSmartValve(_WiserDevice):
    """Class representing a Wiser Smart Valve device"""

    def __init__(self, wiser_rest_controller:_WiserRestController, data: dict, device_type_data: dict):
        super().__init__(data)
        self._wiser_rest_controller = wiser_rest_controller
        self._device_type_data = device_type_data
        self._device_lock_enabled = data.get("DeviceLockEnabled", False)
        self._indentify_active = data.get("IdentifyActive", False)

    def _send_command(self, cmd: dict, device_level: bool = False):
        """
        Send control command to the smart valve
        param cmd: json command structure
        return: boolen - true = success, false = failed
        """
        if device_level:
            result = self._wiser_rest_controller._send_command(WISERDEVICE.format(self.id), cmd)
        else:
            result = self._wiser_rest_controller._send_command(WISERSMARTVALVE.format(self.id), cmd)
        if result:
            _LOGGER.debug(
                "Wiser smart valve - {} command successful".format(
                    inspect.stack()[1].function
                )
            )
        return result

    @property
    def battery(self):
        """Get battery information for smart valve"""
        return _WiserBattery(self._data)

    @property
    def device_lock_enabled(self) -> bool:
        """Get or set smart valve device lock"""
        return self._device_lock_enabled

    @device_lock_enabled.setter
    def device_lock_enabled(self, enable: bool):
        if self._send_command({"DeviceLockEnabled": enable}, True):
            self._device_lock_enabled = enable

    @property
    def current_target_temperature(self) -> float:
        """Get the smart valve current target temperature setting"""
        return tf._from_wiser_temp(self._device_type_data.get("SetPoint"))

    @property
    def current_temperature(self) -> float:
        """Get the current temperature measured by the smart valve"""
        return tf._from_wiser_temp(self._device_type_data.get("MeasuredTemperature"), "current")

    @property
    def identify(self) -> bool:
        """Get or set if the smart valve identify function is enabled"""
        return self._indentify_active

    @identify.setter
    def identify(self, enable: bool = False):
        if self._send_command({"Identify": enable}, True):
            self._indentify_active = enable

    @property
    def mounting_orientation(self) -> str:
        """Get the mouting orientation of the smart valve"""
        return self._device_type_data.get("MountingOrientation")

    @property
    def percentage_demand(self) -> int:
        """Get the current percentage demand of the smart valve"""
        return self._device_type_data.get("PercentageDemand")

    @property
    def room_id(self) -> int:
        """Get smartvalve room id"""
        return self._device_type_data.get("RoomId", 0)
        

class _WiserSmartValveCollection(object):
    """Class holding all wiser smart valves"""

    def __init__(self):
        self._smartvalves = []

    @property
    def all(self) -> dict:
        return list(self._smartvalves)

    @property
    def count(self) -> int:
        return len(self.all)

    def get_by_id(self, id: int) -> _WiserSmartValve:
        """
        Gets a SmartValve object from the SmartValves id
        param id: id of smart valve
        return: _WiserSmartValve object
        """
        try:
            return [
                smartvalve for smartvalve in self.all if smartvalve.id == id
            ][0]
        except IndexError:
            return None
