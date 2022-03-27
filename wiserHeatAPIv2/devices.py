from wiserHeatAPIv2 import heating_actuator
from . import _LOGGER
from .const import TEXT_UNKNOWN

from .rest_controller import _WiserRestController
from .roomstat import _WiserRoomStat, _WiserRoomStatCollection
from .schedule import _WiserScheduleCollection, WiserScheduleTypeEnum
from .smartplug import _WiserSmartPlug, _WiserSmartPlugCollection
from .smartvalve import _WiserSmartValve, _WiserSmartValveCollection
from .heating_actuator import _WiserHeatingActuator, _WiserHeatingActuatorCollection
from .shutter import _WiserShutter, _WiserShutterCollection
from .ufh import _WiserUFHController, _WiserUFHControllerCollection
from .light import _WiserLight, _WiserDimmableLight, _WiserLightCollection

class _WiserDeviceCollection(object):
    """Class holding all wiser devices"""

    def __init__(self, wiser_rest_controller: _WiserRestController, domain_data: dict, schedules: _WiserScheduleCollection):
        self._wiser_rest_controller = wiser_rest_controller
        self._device_data = domain_data.get("Device", {})
        self._domain_data = domain_data
        self._schedules = schedules

        self._smartvalves_collection = _WiserSmartValveCollection()
        self._roomstats_collection = _WiserRoomStatCollection()
        self._smartplugs_collection = _WiserSmartPlugCollection()
        self._heating_actuators_colleciton = _WiserHeatingActuatorCollection()
        self._ufh_controllers_collection = _WiserUFHControllerCollection()
        self._shutters_collection = _WiserShutterCollection()
        self._lights_collection = _WiserLightCollection()

        self._build()

    def _build(self):
        """ Build collection of devices by type"""
        if self._device_data:
            for device in self._device_data:
                # Add smart valve (iTRV) object to collection
                if device.get("ProductType") == "iTRV":
                    smartvalve_info = [
                        smartvalve
                        for smartvalve in self._domain_data.get("SmartValve")
                        if smartvalve.get("id") == device.get("id")
                    ]
                    smartvalve_info[0]["RoomId"] = self._get_temp_device_room_id(self._domain_data, device.get("id"))
                    self._smartvalves_collection._smartvalves.append(
                        _WiserSmartValve(
                            self._wiser_rest_controller,
                            device,
                            smartvalve_info[0]
                        )
                    )

                # Add room stat object to collection
                elif device.get("ProductType") == "RoomStat":
                    roomstat_info = [
                        roomstat
                        for roomstat in self._domain_data.get("RoomStat")
                        if roomstat.get("id") == device.get("id")
                    ]
                    roomstat_info[0]["RoomId"] = self._get_temp_device_room_id(self._domain_data, device.get("id"))
                    self._roomstats_collection._roomstats.append(
                        _WiserRoomStat(
                            self._wiser_rest_controller,
                            device,
                            roomstat_info[0]
                        )
                    )

                # Add smart plug object to collection
                elif device.get("ProductType") == "SmartPlug":
                    smartplug_info = [
                        smartplug
                        for smartplug in self._domain_data.get("SmartPlug")
                        if smartplug.get("id") == device.get("id")
                    ]
                    smartplug_schedule = [
                        schedule
                        for schedule in self._schedules.get_by_type(WiserScheduleTypeEnum.onoff)
                        if schedule.id == smartplug_info[0].get("ScheduleId")
                    ]
                    self._smartplugs_collection._smartplugs.append(
                        _WiserSmartPlug(
                            self._wiser_rest_controller,
                            device,
                            smartplug_info[0],
                            smartplug_schedule[0] if len(smartplug_schedule) > 0 else []
                        )
                    )

                # Add heating actuator object to collection
                elif device.get("ProductType") == "HeatingActuator":
                    heating_actuator_info = [
                        heating_actuator
                        for heating_actuator in self._domain_data.get("HeatingActuator")
                        if heating_actuator.get("id") == device.get("id")
                    ]
                    heating_actuator_info[0]["RoomId"] = self._get_temp_device_room_id(self._domain_data, device.get("id"))
                    self._heating_actuators_colleciton._heating_actuators.append(
                        _WiserHeatingActuator(
                            self._wiser_rest_controller,
                            device,
                            heating_actuator_info[0]
                        )
                    )

                # Add ufh controller object to collection
                elif device.get("ProductType") == "UnderFloorHeating":
                    ufh_controller_info = [
                        ufh_controller
                        for ufh_controller in self._domain_data.get("UnderFloorHeating")
                        if ufh_controller.get("id") == device.get("id")
                    ]
                    ufh_controller_info[0]["RoomId"] = self._get_temp_device_room_id(self._domain_data, device.get("id"))
                    self._ufh_controllers_collection._ufh_controllers.append(
                        _WiserUFHController(
                            self._wiser_rest_controller,
                            device,
                            ufh_controller_info[0]
                        )
                    )

                # Add shutter object to collection
                elif device.get("ProductType") == "Shutter":
                    shutter_info = [
                        shutter
                        for shutter in self._domain_data.get("Shutter")
                        if shutter.get("DeviceId") == device.get("id")
                    ]
                    shutter_schedule = [
                        schedule
                        for schedule in self._schedules.get_by_type(WiserScheduleTypeEnum.level)
                        if schedule.id == shutter_info[0].get("ScheduleId", 0)
                    ]
                    self._shutters_collection._shutters.append(
                        _WiserShutter(
                            self._wiser_rest_controller,
                            device,
                            shutter_info[0],
                            shutter_schedule[0] if len(shutter_schedule) > 0 else []
                        )
                    )

                # Add light object to collection
                elif device.get("ProductType") in ["OnOffLight", "DimmableLight"]:
                    light_info = [
                        light
                        for light in self._domain_data.get("Light")
                        if light.get("DeviceId") == device.get("id")
                    ]
                    light_schedule = [
                        schedule
                        for schedule in self._schedules.get_by_type(WiserScheduleTypeEnum.level)
                        if schedule.id == light_info[0].get("ScheduleId")
                    ]
                    if device.get("ProductType") == "DimmableLight":
                        self._lights_collection._lights.append(
                            _WiserDimmableLight(
                                self._wiser_rest_controller,
                                device,
                                light_info[0],
                                light_schedule[0] if len(light_schedule) > 0 else []
                            )
                        )
                    else:
                        self._lights_collection._lights.append(
                            _WiserLight(
                                self._wiser_rest_controller,
                                device,
                                light_info[0],
                                light_schedule[0] if len(light_schedule) > 0 else []
                            )
                        )
                    
    def _get_temp_device_room_id(self, domain_data: dict, device_id: int) -> int:
        rooms = domain_data.get("Room")
        for room in rooms:
            room_device_list = []
            room_device_list.extend(room.get("SmartValveIds",[]))
            room_device_list.extend(room.get("HeatingActuatorIds", []))
            room_device_list.append(room.get("RoomStatId"))
            room_device_list.append(room.get("UnderFloorHeatingId"))
            if device_id in room_device_list:
                return room.get("id")
        return 0



    @property
    def all(self):
        return (
            list(self._smartvalves_collection.all) 
            + list(self._roomstats_collection.all) 
            + list(self._smartplugs_collection.all)
            + list(self._heating_actuators_colleciton.all)
            + list(self._ufh_controllers_collection.all)
            + list(self._shutters_collection.all)
            + list(self._lights_collection.all)
        )

    @property
    def count(self) -> int:
        return len(self.all)

    @property
    def heating_actuators(self):
        return self._heating_actuators_colleciton

    @property
    def lights(self):
        return self._lights_collection

    @property
    def roomstats(self):
        return self._roomstats_collection

    @property
    def shutters(self):
        return self._shutters_collection

    @property
    def smartplugs(self):
        return self._smartplugs_collection

    @property
    def smartvalves(self):
        return self._smartvalves_collection

    @property
    def ufh_controllers(self):
        return self._ufh_controllers_collection

    def get_by_id(self, id: int):
        """
        Gets a device object from the devices id
        param id: id of device
        return: _WiserSmartValve, _Wiser_RoomStat or _WiserSmartPlug object
        """
        try:
            return [device for device in self.all if device.id == id][0]
        except IndexError:
            return None

    def get_by_room_id(self, room_id:int) -> list:
        """
        Gets a list of devices belonging to the room id
        param room_id: the id of the room
        return: _WiserSmartValve, _Wiser_RoomStat or _WiserSmartPlug object
        """
        try:
            return [device for device in self.all if device.room_id == room_id]
        except IndexError:
            return None

    def get_by_node_id(self, node_id: int):
        """
        Gets a device object from the devices zigbee node id
        param node_id: zigbee node id of device
        return: _WiserSmartValve, _Wiser_RoomStat or _WiserSmartPlug object
        """
        try:
            return [device for device in self.all if device.node_id == node_id][0]
        except IndexError:
            return None

    def get_by_serial_number(self, serial_number:str):
        """
        Gets a device object from the devices serial number
        param node_id: serial number of device
        return: _WiserSmartValve, _Wiser_RoomStat or _WiserSmartPlug object
        """
        try:
            return [device for device in self.all if device.serial_number == serial_number][0]
        except IndexError:
            return None

    def get_by_parent_node_id(self, node_id:int) -> list:
        """
        Gets a list of device from the devices zigbee parent node id
        param node_id: zigbee parent node id of device
        return: List of _WiserSmartValve, _Wiser_RoomStat or _WiserSmartPlug object
        """
        try:
            return [device for device in self.all if device.parent_node_id == node_id]
        except IndexError:
            return None  

    