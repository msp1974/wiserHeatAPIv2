from . import _LOGGER
from .const import TEXT_UNKNOWN

from .rest_controller import _WiserRestController
from .roomstat import _WiserRoomStat, _WiserRoomStatCollection
from .schedule import _WiserScheduleCollection
from .smartplug import _WiserSmartPlug, _WiserSmartPlugCollection
from .smartvalve import _WiserSmartValve, _WiserSmartValveCollection

class _WiserDeviceCollection(object):
    """Class holding all wiser devices"""

    def __init__(self, wiser_rest_controller: _WiserRestController, domain_data: dict, schedules: _WiserScheduleCollection):
        self._wiser_rest_controller = wiser_rest_controller
        self._device_data = domain_data.get("Device", {})
        self._domain_data = domain_data
        self._schedules = schedules.all

        self._smartvalves_collection = _WiserSmartValveCollection()
        self._roomstats_collection = _WiserRoomStatCollection()
        self._smartplugs_collection = _WiserSmartPlugCollection()

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
                        for schedule in self._schedules
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


    @property
    def all(self):
        return list(self._smartvalves_collection.all) + list(self._roomstats_collection.all) + list(self._smartplugs_collection.all)

    @property
    def count(self) -> int:
        return len(self.all)

    @property
    def smartvalves(self):
        return self._smartvalves_collection

    @property
    def roomstats(self):
        return self._roomstats_collection

    @property
    def smartplugs(self):
        return self._smartplugs_collection

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

    def get_by_room_name(self, room_name:str):
        pass

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

    