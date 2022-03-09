from . import _LOGGER

from .device import _WiserDevice
from .helpers import _WiserTemperatureFunctions as tf
from .rest_controller import _WiserRestController

from .const import TEMP_MAXIMUM, TEMP_MINIMUM, TEMP_OFF, TEXT_UNKNOWN, WISERUFHCONTROLLER, WISERDEVICE

import inspect

class _WiserUFHRelay(object):
    def __init__(self, relay_data: dict):
        self.demand_percentage = relay_data.get("DemandPercentage", 0)
        self.polarity = relay_data.get("Polarity", False)
        self.id = relay_data.get("id", 0)


class _WiserUFHController(_WiserDevice):
    """Class representing a Wiser Heating Actuator device"""

    def __init__(self, wiser_rest_controller:_WiserRestController, data: dict, device_type_data: dict):
        super().__init__(data)
        self._wiser_rest_controller = wiser_rest_controller
        self._device_type_data = device_type_data
        self._device_lock_enabled = False
        self._indentify_active = data.get("IdentifyActive", False)
        self._relays = []
        self.build_relay_collection(self._device_type_data.get("Relays", []))

    def build_relay_collection(self, relays: dict):
        """Build collection of relays"""
        for relay in relays:
            self._relays.append(_WiserUFHRelay(relay))

    def _send_command(self, cmd: dict, device_level: bool = False):
        """
        Send control command to the heating actuator
        param cmd: json command structure
        return: boolen - true = success, false = failed
        """
        if device_level:
            result = self._wiser_rest_controller._send_command(WISERDEVICE.format(self.id), cmd)
        else:
            result = self._wiser_rest_controller._send_command(WISERUFHCONTROLLER.format(self.id), cmd)
        if result:
            _LOGGER.debug(
                "Wiser UFH Controller - {} command successful".format(
                    inspect.stack()[1].function
                )
            )
        return result

    @property
    def current_temperature(self) -> float:
        """Get the current temperature measured by the smart valve"""
        return tf._from_wiser_temp(self._device_type_data.get("MeasuredTemperature"), "current")

    @property
    def device_lock_enabled(self) -> bool:
        """Get or set heating actuator device lock"""
        return self._device_lock_enabled

    @device_lock_enabled.setter
    def device_lock_enabled(self, enable: bool):
        if self._send_command({"DeviceLockEnabled": enable}, True):
            self._device_lock_enabled = enable

    @property
    def dew_detected(self) -> bool:
        """Get if dew detected"""
        return self._device_type_data.get("DewDetected", None)

    @property
    def identify(self) -> bool:
        """Get or set if the smart valve identify function is enabled"""
        return self._indentify_active

    @identify.setter
    def identify(self, enable: bool = False):
        if self._send_command({"Identify": enable}, True):
            self._indentify_active = enable

    @property
    def interlock_active(self) -> bool:
        """Get if interlock active"""
        return self._device_type_data.get("InterlockActive", None)

    @property
    def is_full_strip(self) -> bool:
        """Get if full strip"""
        return self._device_type_data.get("IsFullStrip", None)

    @property
    def max_floor_temperature(self) -> int:
        """Get the max heat floor temperature"""
        return self._device_type_data.get("MaxHeatFloorTemperature", TEMP_MAXIMUM)

    @property
    def min_floor_temperature(self) -> int:
        """Get the min heat floor temperature"""
        return self._device_type_data.get("MinHeatFloorTemperature", TEMP_OFF)

    @property
    def name(self) -> str:
        """Get name of UFH controller"""
        return self._device_type_data.get("Name", TEXT_UNKNOWN)

    @property
    def output_type(self) -> str:
        """Get output type"""
        return self._device_type_data.get("OutputType", TEXT_UNKNOWN)

    @property
    def relays(self) -> list:
        return self._relays

    @property
    def room_id(self) -> int:
        """Get heating actuator room id"""
        return self._device_type_data.get("RoomId", 0)
      

class _WiserUFHControllerCollection(object):
    """Class holding all wiser heating actuators"""

    def __init__(self):
        self._ufh_controllers = []

    @property
    def all(self) -> dict:
        return list(self._ufh_controllers)

    @property
    def count(self) -> int:
        return len(self.all)

    def get_by_id(self, id: int) -> _WiserUFHController:
        """
        Gets a Heating Actuator object from the Heating Actuators id
        param id: id of smart valve
        return: _WiserSmartValve object
        """
        try:
            return [
                ufh_controller for ufh_controller in self.all if ufh_controller.id == id
            ][0]
        except IndexError:
            return None
