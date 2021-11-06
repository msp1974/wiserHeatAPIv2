#!/usr/bin/env python3
"""
# Wiser API Version 2

angelosantagata@gmail.com
msparker@sky.com


https://github.com/asantaga/wiserheatingapi


This API allows you to get information from and control your wiserhub.
"""

# TODO: Keep objects and update instead of recreating on hub update
# TODO: Update entity values after commend issued to get current values
from .const import (
    DEFAULT_AWAY_MODE_TEMP,
    DEFAULT_DEGRADED_TEMP,
    HW_OFF,
    HW_ON,
    MAX_BOOST_INCREASE,
    TEMP_ERROR,
    TEMP_MINIMUM,
    TEMP_MAXIMUM,
    TEMP_OFF,
    WiserModeEnum,
    WiserUnitsEnum,
    WISERHUBDOMAIN,
    WISERHUBNETWORK,
    WISERHUBSCHEDULES
)
from .device import _WiserDevice
from .discovery import WiserDiscovery
from .exceptions import (
    WiserHubAuthenticationError,
    WiserHubConnectionError,
    WiserHubRESTError
)
from .heating import _WiserHeating
from .hot_water import _WiserHotwater
from .rest_controller import _WiserRestController, _WiserConnection
from .room import _WiserRoom
from .roomstat import _WiserRoomStat
from .schedule import _WiserSchedule
from .smart_plug import _WiserSmartPlug
from .smart_valve import _WiserSmartValve
from .system import _WiserSystem
import logging

__VERSION__ = "0.0.2"
_LOGGER = logging.getLogger(__name__)


class WiserAPI:
    """
    Main api class to access all entities and attributes of wiser system
    """
    def __init__(self, host: str, secret: str, units: WiserUnitsEnum = WiserUnitsEnum.metric):
        
        # Connection variables
        self._wiser_api_connection = _WiserConnection()
        
        # Main data stores
        self._domain_data = {}
        self._network_data = {}
        self._schedule_data = {}

        # Data stores for exposed properties
        self._schedules = []
        self._system = None
        self._devices = []
        self._smart_valves = []
        self._smart_plugs = []
        self._room_stats = []
        self._rooms = []
        self._hotwater = None
        self._heating = []

        _LOGGER.info("WiserHub API Initialised : Version {}".format(__VERSION__))

        # Set default unit system
        self._wiser_api_connection.units = units
        _LOGGER.info("Units set to {}".format(self._wiser_api_connection.units.name.title()))


        # Set hub secret to global object
        self._wiser_api_connection.secret = secret

        # Do hub discovery if null IP is passed when initialised
        if host is None:
            wiser_discover = WiserDiscovery()
            hub = wiser_discover.discover_hub()
            if len(hub) > 0:
                self._wiser_api_connection.hubName = hub[0]["name"]
                self._wiser_api_connection.host = hub[0]["hostname"]

                _LOGGER.debug(
                    "Hub: {}, Host: {}".format(
                        self._wiser_api_connection.hubName, self._wiser_api_connection.host
                    )
                )
            else:
                _LOGGER.error("No Wiser hub discovered on network")
        else:
            self._wiser_api_connection.host = host

        # Read hub data if hub IP and secret exist
        if (
            self._wiser_api_connection.host is not None
            and self._wiser_api_connection.secret is not None
        ):
            self.read_hub_data()
            # TODO - Add validation fn to check for no devs, rooms etc
        else:
            _LOGGER.error("No connection info")

    def read_hub_data(
        self, domain: bool = True, network: bool = True, schedule: bool = True
    ):
        """Read all data from hub and populate objects"""
        # Read hub data endpoints
        hub_data = _WiserRestController(self._wiser_api_connection)
        if domain:
            self._domain_data = hub_data._getHubData(WISERHUBDOMAIN)
        if network:
            self._network_data = hub_data._getHubData(WISERHUBNETWORK)
        if schedule:
            self._schedule_data = hub_data._getHubData(WISERHUBSCHEDULES)

        # Schedules
        self._schedules = []
        for schedule_type in self._schedule_data:
            for schedule in self._schedule_data.get(schedule_type):
                self._schedules.append(_WiserSchedule(schedule_type, schedule))

        # Devices
        self._devices = []
        self._system = None
        self._smart_valves = []
        self._room_stats = []
        self._smart_plugs = []

        if self._domain_data.get("Device"):
            for device in self._domain_data.get("Device"):
                # Add to generic device list
                self._devices.append(_WiserDevice(device))

                # Add device to specific device type
                if device.get("ProductType") == "Controller":
                    self._system = _WiserSystem(
                        self._domain_data.get("System"),
                        device,
                        self._network_data,
                        self._domain_data.get("Cloud"),
                    )

                elif device.get("ProductType") == "iTRV":
                    # Add smart valve (iTRV) object
                    smart_valve_info = [
                        smart_valve
                        for smart_valve in self._domain_data.get("SmartValve")
                        if smart_valve.get("id") == device.get("id")
                    ]
                    self._smart_valves.append(
                        _WiserSmartValve(device, smart_valve_info[0])
                    )

                elif device.get("ProductType") == "RoomStat":
                    # Add room stat object
                    room_stat_info = [
                        room_stat
                        for room_stat in self._domain_data.get("RoomStat")
                        if room_stat.get("id") == device.get("id")
                    ]
                    self._room_stats.append(_WiserRoomStat(device, room_stat_info[0]))

                elif device.get("ProductType") == "SmartPlug":
                    # Add smart plug object
                    smart_plug_info = [
                        smart_plug
                        for smart_plug in self._domain_data.get("SmartPlug")
                        if smart_plug.get("id") == device.get("id")
                    ]
                    smart_plug_schedule = [
                        schedule
                        for schedule in self.schedules
                        if schedule.id == smart_plug_info[0].get("ScheduleId")
                    ]
                    self._smart_plugs.append(
                        _WiserSmartPlug(
                            device, smart_plug_info[0], smart_plug_schedule[0]
                        )
                    )

        # Add room objects
        self._rooms = []
        for room in self._domain_data.get("Room", []):
            schedule = self.get_schedule_by_id(room.get("ScheduleId", 0))
            devices = [
                device
                for device in self.devices
                if (
                    device.id in room.get("SmartValveIds", ["-1"])
                    or device.id == room.get("RoomStatId", "-1")
                    or device.id
                    in [
                        smartplug.id
                        for smartplug in self._smart_plugs
                        if smartplug.room_id == room.get("id", 0)
                    ]
                )
            ]
            self._rooms.append(
                _WiserRoom(
                    room,
                    schedule,
                    devices,
                )
            )

        # Add hotwater object
        self._hotwater = None
        if self._domain_data.get("HotWater"):
            self._hotwater = _WiserHotwater(
                self._domain_data.get("HotWater", {})[0],
                self.get_schedule_by_id(
                    self._domain_data.get("HotWater", {})[0].get("ScheduleId", 0)
                ),
            )

        # Add heating object
        # TODO: Only pass rooms on relevant heating channel
        self._heating = []
        if self._domain_data.get("HeatingChannel"):
            for heat_channel in self._domain_data.get("HeatingChannel", []):
                self._heating.append(_WiserHeating(heat_channel, self.rooms))

        # If gets here with no exceptions then success and return true
        return True

    # API properties
    @property
    def devices(self):
        """List of device entities attached to the Wiser Hub"""
        return self._devices

    @property
    def heating(self):
        """List of heating channel entities on the Wiser Hub"""
        return self._heating

    @property
    def hotwater(self):
        """List of hot water entities on the Wiser Hub"""
        return self._hotwater

    @property
    def rooms(self):
        """List of room entities configured on the Wiser Hub"""
        return self._rooms

    @property
    def room_stats(self):
        """List of room stat entities connected to the Wiser Hub"""
        return self._room_stats

    @property
    def schedules(self):
        """List of schedule entities on the Wiser Hub"""
        return self._schedules

    @property
    def smart_plugs(self):
        """List of smart plug entities connected to the Wiser Hub"""
        return self._smart_plugs

    @property
    def smart_valves(self):
        """List of smart valve (iTRV) entities connected to the Wiser Hub"""
        return self._smart_valves

    @property
    def system(self):
        """Entity of the Wiser Hub"""
        return self._system

    @property
    def units(self) -> WiserUnitsEnum:
        """Get or set units for temperature"""
        return self._wiser_api_connection.units

    @units.setter
    def units(self, units: WiserUnitsEnum):
        self._wiser_api_connection.units = units


    # Functions to get entities by id or name
    # Rooms
    def get_room_by_id(self, id: int):
        """
        Gets a room object from the rooms id
        param id: id of room
        return: _WiserRoom object
        """
        try:
            return [room for room in self.rooms if room.id == id][0]
        except IndexError:
            return None

    def get_room_by_name(self, name: str):
        """
        Gets a room object from the rooms name
        param name: name of room
        return: _WiserRoom object
        """
        try:
            return [room for room in self.rooms if room.name == name][0]
        except IndexError:
            return None

    def get_room_by_device_id(self, device_id: int):
        """
        Gets a room object for the room a device id belongs to
        param device_id: the id of the device
        return: _WiserRoom object
        """
        for room in self.rooms:
            for device in room.devices:
                if device.id == device_id:
                    return room
        return None

    # Schedules
    def get_schedule_by_id(self, id: int):
        """
        Gets a schedule object from the schedules id
        param id: id of schedule
        return: _WiserSchedule object
        """
        try:
            return [schedule for schedule in self.schedules if schedule.id == id][0]
        except IndexError:
            return None

    def get_schedule_by_name(self, name: str):
        """
        Gets a schedule object from the schedules name
        (room name, smart plug name, hotwater)
        param name: name of schedule
        return: _WiserSchedule object
        """
        try:
            return [schedule for schedule in self.schedules if schedule.name == name][0]
        except IndexError:
            return None

    # Devices
    def get_device_by_id(self, id: int):
        """
        Gets a device object from the devices id
        param id: id of device
        return: _WiserDevice object
        """
        try:
            return [device for device in self.devices if device.id == id][0]
        except IndexError:
            return None

    def get_device_by_node_id(self, node_id: int):
        """
        Gets a device object from the devices zigbee node id
        param node_id: zigbee node id of device
        return: _WiserDevice object
        """
        try:
            return [device for device in self.devices if device.node_id == node_id][0]
        except IndexError:
            return None

    def get_devices_by_room_id(self, room_id: int):
        """
        Gets a list of devices belonging to the room id
        param room_id: the id of the room
        return: _WiserDevice list object
        """
        try:
            return self.get_room_by_id(room_id).devices
        except AttributeError:
            return None

    # Smartvalves
    def get_smart_valve_by_id(self, id: int):
        """
        Gets a SmartValve object from the SmartValves id
        param id: id of smart valve
        return: _WiserSmartValve object
        """
        try:
            return [
                smart_valve for smart_valve in self.smart_valves if smart_valve.id == id
            ][0]
        except IndexError:
            return None

    # Smartplugs
    def get_smart_plug_by_id(self, id: int):
        """
        Gets a SmartPlug object from the SmartPlugs id
        param id: id of smart plug
        return: _WiserSmartPlug object
        """
        try:
            return [
                smart_plug for smart_plug in self.smart_plugs if smart_plug.id == id
            ][0]
        except IndexError:
            return None

    # Roomstats
    def get_room_stat_by_id(self, id: int):
        """
        Gets a RoomStat object from the RoomStatss id
        param id: id of room stat
        return: _WiserRoomStat object
        """
        try:
            return [room_stat for room_stat in self.room_stats if room_stat.id == id][0]
        except IndexError:
            return None
