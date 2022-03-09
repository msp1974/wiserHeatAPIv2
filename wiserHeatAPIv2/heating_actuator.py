from . import _LOGGER

from .device import _WiserDevice
from .helpers import _WiserTemperatureFunctions as tf
from .rest_controller import _WiserRestController

from .const import TEMP_OFF, TEXT_UNKNOWN, WISERHEATINGACTUATOR, WISERDEVICE

import inspect


class _WiserHeatingActuator(_WiserDevice):
    """Class representing a Wiser Heating Actuator device"""

    def __init__(self, wiser_rest_controller:_WiserRestController, data: dict, device_type_data: dict):
        super().__init__(data)
        self._wiser_rest_controller = wiser_rest_controller
        self._device_type_data = device_type_data
        self._device_lock_enabled = False
        self._indentify_active = data.get("IdentifyActive", False)

    def _send_command(self, cmd: dict, device_level: bool = False):
        """
        Send control command to the heating actuator
        param cmd: json command structure
        return: boolen - true = success, false = failed
        """
        if device_level:
            result = self._wiser_rest_controller._send_command(WISERDEVICE.format(self.id), cmd)
        else:
            result = self._wiser_rest_controller._send_command(WISERHEATINGACTUATOR.format(self.id), cmd)
        if result:
            _LOGGER.debug(
                "Wiser heating actuator - {} command successful".format(
                    inspect.stack()[1].function
                )
            )
        return result

    @property
    def current_target_temperature(self) -> float:
        """Get the smart valve current target temperature setting"""
        return tf._from_wiser_temp(self._device_type_data.get("OccupiedHeatingSetPoint", TEMP_OFF))

    @property
    def current_temperature(self) -> float:
        """Get the current temperature measured by the smart valve"""
        return tf._from_wiser_temp(self._device_type_data.get("MeasuredTemperature", TEMP_OFF), "current")

    @property
    def delivered_power(self) -> int:
        """Get the amount of current throught the plug over time"""
        return self._device_type_data.get("CurrentSummationDelivered", 0)

    @property
    def device_lock_enabled(self) -> bool:
        """Get or set heating actuator device lock"""
        return self._device_lock_enabled

    @device_lock_enabled.setter
    def device_lock_enabled(self, enable: bool):
        if self._send_command({"DeviceLockEnabled": enable}, True):
            self._device_lock_enabled = enable


    @property
    def identify(self) -> bool:
        """Get or set if the smart valve identify function is enabled"""
        return self._indentify_active

    @identify.setter
    def identify(self, enable: bool = False):
        if self._send_command({"Identify": enable}, True):
            self._indentify_active = enable

    @property
    def instantaneous_power(self) -> int:
        """Get the amount of current throught the plug now"""
        return self._device_type_data.get("InstantaneousDemand", 0)

    @property
    def output_type(self) -> str:
        """Get output type"""
        return self._device_type_data.get("OutputType", TEXT_UNKNOWN)

    @property
    def room_id(self) -> int:
        """Get heating actuator room id"""
        return self._device_type_data.get("RoomId", 0)
      

class _WiserHeatingActuatorCollection(object):
    """Class holding all wiser heating actuators"""

    def __init__(self):
        self._heating_actuators = []

    @property
    def all(self) -> dict:
        return list(self._heating_actuators)

    @property
    def count(self) -> int:
        return len(self.all)

    def get_by_id(self, id: int) -> _WiserHeatingActuator:
        """
        Gets a Heating Actuator object from the Heating Actuators id
        param id: id of smart valve
        return: _WiserSmartValve object
        """
        try:
            return [
                heating_actuator for heating_actuator in self.all if heating_actuator.id == id
            ][0]
        except IndexError:
            return None
