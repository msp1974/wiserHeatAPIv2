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

import enum
import inspect
import json
import logging
import requests
import sys

from datetime import datetime, timezone
from ruamel.yaml import YAML
from time import sleep
from typing import cast
from zeroconf import ServiceBrowser, ServiceStateChange, Zeroconf

__VERSION__ = "0.0.2"
_LOGGER = logging.getLogger(__name__)

# TODO: Remove this in production!!!!
# Set traceback limit
TRACEBACK_LIMIT = 3
sys.tracebacklimit = TRACEBACK_LIMIT

# Temperature Constants
DEFAULT_AWAY_MODE_TEMP = 10.5
DEFAULT_DEGRADED_TEMP = 18
HW_ON = 110
HW_OFF = -20
MAX_BOOST_INCREASE = 5
TEMP_ERROR = 2000
TEMP_MINIMUM = 5
TEMP_MAXIMUM = 30
TEMP_OFF = -20

# Battery Constants
ROOMSTAT_MIN_BATTERY_LEVEL = 1.7
ROOMSTAT_FULL_BATTERY_LEVEL = 2.7
TRV_FULL_BATTERY_LEVEL = 3.0
TRV_MIN_BATTERY_LEVEL = 2.5

# Other Constants
REST_TIMEOUT = 15


# Text Values
TEXT_DEGREESC = "DegreesC"
TEXT_HEATING = "Heating"
TEXT_OFF = "Off"
TEXT_ON = "On"
TEXT_ONOFF = "OnOff"
TEXT_STATE = "State"
TEXT_TEMP = "Temp"
TEXT_TIME = "Time"
TEXT_UNKNOWN = "Unknown"
TEXT_WEEKDAYS = "Weekdays"
TEXT_WEEKENDS = "Weekends"

# Day Value Lists
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
WEEKENDS = ["Saturday", "Sunday"]
SPECIAL_DAYS = [TEXT_WEEKDAYS, TEXT_WEEKENDS]

# Wiser Hub Rest Api URL Constants
WISERHUBURL = "http://{}/data/v2/"
WISERHUBDOMAIN = WISERHUBURL + "domain/"
WISERHUBNETWORK = WISERHUBURL + "network/"
WISERHUBSCHEDULES = WISERHUBURL + "schedules/"
WISERSYSTEM = "System"
WISERHOTWATER = "HotWater/{}"
WISERROOM = "Room/{}"
WISERSMARTVALVE = "SmartValve/{}"
WISERROOMSTAT = "RoomStat/{}"
WISERSMARTPLUG = "SmartPlug/{}"


# Exception Handlers
class WiserHubConnectionError(Exception):
    pass


class WiserHubAuthenticationError(Exception):
    pass


class WiserHubRESTError(Exception):
    pass


class WiserHubNotImplementedError(Exception):
    _LOGGER.info("Function not yet implemented")
    pass


# Enums
class WiserModeEnum(enum.Enum):
    off = "Off"
    auto = "Auto"
    manual = "Manual"


class WiserHotWaterStateEnum(enum.Enum):
    off = "Off"
    on = "On"


class WiserAwayActionEnum(enum.Enum):
    off = "Off"
    no_change = "NoChange"


class WiserUnitsEmun(enum.Enum):
    imperial = "imperial"
    metric = "metric"


# Connection info class
class _WiserConnection:
    def __init(self):
        self.host = None
        self.secret = None
        self.hub_name = None
        self.units = WiserUnitsEmun.metric


# Global variables
_wiser_api_connection = _WiserConnection()

class WiserAPI:
    """
    Main api class to access all entities and attributes of wiser system
    """
    def __init__(self, host: str, secret: str, units: WiserUnitsEmun = WiserUnitsEmun.metric):
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
        _wiser_api_connection.units = units
        _LOGGER.info("Units set to {}".format(_wiser_api_connection.units.name.title()))


        # Set hub secret to global object
        _wiser_api_connection.secret = secret

        # Do hub discovery if null IP is passed when initialised
        if host is None:
            wiser_discover = WiserDiscovery()
            hub = wiser_discover.discover_hub()
            if len(hub) > 0:
                _wiser_api_connection.hubName = hub[0]["name"]
                _wiser_api_connection.host = hub[0]["hostname"]

                _LOGGER.info(
                    "Hub: {}, Host: {}".format(
                        _wiser_api_connection.hubName, _wiser_api_connection.host
                    )
                )
            else:
                _LOGGER.error("No Wiser hub discovered on network")
        else:
            _wiser_api_connection.host = host

        # Read hub data if hub IP and secret exist
        if (
            _wiser_api_connection.host is not None
            and _wiser_api_connection.secret is not None
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
        hub_data = _WiserRestController()
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
    def units(self) -> WiserUnitsEmun:
        """Get or set units for temperature"""
        return _wiser_api_connection.units

    @units.setter
    def units(self, units: WiserUnitsEmun):
        _wiser_api_connection.units = units


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


class _WiserRestController:
    """
    Class to handle getting data from and sending commands to a wiser hub
    """

    def _getHeaders(self):
        """
        Define headers for wiser hub api calls
        return: json object
        """
        return {
            "SECRET": _wiser_api_connection.secret,
            "Content-Type": "application/json;charset=UTF-8",
        }

    def _getHubData(self, url: str):
        """
        Read data from hub and raise errors if fails
        param url: url of hub rest api endpoint
        return: json object
        """
        url = url.format(_wiser_api_connection.host)
        try:
            response = requests.get(
                url,
                headers=self._getHeaders(),
                timeout=REST_TIMEOUT,
            )
            response.raise_for_status()

        except requests.exceptions.ConnectTimeout:
            raise WiserHubConnectionError(
                "Connection timed out trying to update from Wiser Hub"
            )

        except requests.HTTPError as ex:
            if ex.response.status_code == 401:
                raise WiserHubAuthenticationError(
                    "Error authenticating to Wiser Hub.  Check your secret key"
                )
            elif ex.response.status_code == 404:
                raise WiserHubRESTError("Rest endpoint not found on Wiser Hub")
            else:
                raise WiserHubRESTError(
                    "Unknown error getting data from Wiser Hub.  Error code is: {}".format(
                        ex.response.status_code
                    )
                )

        except requests.exceptions.ConnectionError:
            raise WiserHubConnectionError(
                "Connection error trying to update from Wiser Hub"
            )

        except requests.exceptions.ChunkedEncodingError:
            raise WiserHubConnectionError(
                "Chunked Encoding error trying to update from Wiser Hub"
            )

        return response.json()

    def _patch_hub_data(self, url: str, patch_data: dict):
        """
        Send patch update to hub and raise errors if fails
        param url: url of hub rest api endpoint
        param patchData: json object containing command and values to set
        return: boolean
        """
        try:
            response = requests.patch(
                url=url,
                headers=self._getHeaders(),
                json=patch_data,
                timeout=REST_TIMEOUT,
            )
            # TODO: Improve error handling (maybe inc retry?)
            response.raise_for_status()

        except requests.exceptions.ConnectTimeout:
            raise WiserHubConnectionError(
                "Connection timed out trying to send command to Wiser Hub"
            )

        except requests.HTTPError as ex:
            if ex.response.status_code == 401:
                raise WiserHubAuthenticationError(
                    "Error authenticating to Wiser Hub.  Check your secret key"
                )
            elif ex.response.status_code == 404:
                raise WiserHubRESTError("Rest endpoint not found on Wiser Hub")
            else:
                raise WiserHubRESTError(
                    "Error setting {} , error {} {}".format(
                        patch_data, response.status_code, response.text
                    )
                )

        except requests.exceptions.ConnectionError:
            raise WiserHubConnectionError(
                "Connection error trying to send command to Wiser Hub"
            )

        except requests.exceptions.ChunkedEncodingError:
            raise WiserHubConnectionError(
                "Chunked Encoding error trying to send command to Wiser Hub"
            )

        return True

    def _send_command(self, url: str, command_data: dict):
        """
        Send control command to hub and raise errors if fails
        param url: url of hub rest api endpoint
        param patchData: json object containing command and values to set
        return: boolean
        """
        url = WISERHUBDOMAIN.format(_wiser_api_connection.host) + url
        _LOGGER.debug(
            "Sending command to url: {} with parameters {}".format(url, command_data)
        )
        return self._patch_hub_data(url, command_data)

    def _send_schedule(self, url: str, schedule_data: dict):
        """
        Send schedule to hub and raise errors if fails
        param url: url of hub rest api endpoint
        param patchData: json object containing command and values to set
        return: boolean
        """
        url = url.format(_wiser_api_connection.host)
        _LOGGER.debug(
            "Sending schedule to url: {} with data {}".format(url, schedule_data)
        )
        return self._patch_hub_data(url, schedule_data)


class WiserDiscovery:
    """
    Class to handle mDns discovery of a wiser hub on local network
    Use discover_hub() to return list of mDns responses.
    """

    def __init__(self):
        self._discovered_hubs = []

    def _zeroconf_on_service_state_change(
        self,
        zeroconf: Zeroconf,
        service_type: str,
        name: str,
        state_change: ServiceStateChange,
    ) -> None:
        """
        Look for Wiser Hub in discovered services and set IP and Name in
        global vars
        """
        if state_change is ServiceStateChange.Added:
            if "WiserHeat" in name:
                info = zeroconf.get_service_info(service_type, name)
                if info:
                    addresses = [
                        "%s:%d" % (addr, cast(int, info.port))
                        for addr in info.parsed_addresses()
                    ]
                    hub = {
                        "ip": addresses[0].replace(":80", ""),
                        "name": info.server.replace(".local.", ""),
                        "hostname": info.server.replace(".local.", ".local").lower(),
                    }
                    _LOGGER.info(
                        "Discovered Hub {} with IP Address {}".format(
                            info.server.replace(".local.", ""),
                            addresses[0].replace(":80", ""),
                        )
                    )
                    self._discovered_hubs.append(hub)

    def discover_hub(self, min_search_time: int = 2, max_search_time: int = 10):
        """
        Call zeroconf service browser to find Wiser hubs on the local network.
        param (optional) min_search_time: min seconds to wait for responses before returning
        param (optional) max_search_time: max seconds to wait for responses before returning
        return: list of discovered hubs
        """
        timeout = 0

        zeroconf = Zeroconf()
        services = ["_http._tcp.local."]
        ServiceBrowser(
            zeroconf, services, handlers=[self._zeroconf_on_service_state_change]
        )

        while (
            len(self._discovered_hubs) < 1 or timeout < min_search_time * 10
        ) and timeout < max_search_time * 10:
            sleep(0.1)
            timeout += 1

        zeroconf.close()
        return self._discovered_hubs


class _WiserDevice(object):
    """Class representing a wiser device"""

    def __init__(self, data: dict):
        self._data = data
        self.signal = _WiserZwaveSignal(data)

    @property
    def firmware_version(self) -> str:
        """Get firmware version of device"""
        return self._data.get("ActiveFirmwareVersion", TEXT_UNKNOWN)

    @property
    def id(self) -> int:
        """Get id of device"""
        return self._data.get("id")

    @property
    def model(self) -> str:
        """Get model of device"""
        return self._data.get("ModelIdentifier", TEXT_UNKNOWN)

    @property
    def node_id(self) -> int:
        """Get zigbee node id of device"""
        return self._data.get("NodeId", 0)

    @property
    def parent_node_id(self) -> int:
        """Get zigbee node id of device this device is connected to"""
        return self._data.get("ParentNodeId", 0)

    @property
    def product_type(self) -> str:
        """Get product type of device"""
        return self._data.get("ProductType", TEXT_UNKNOWN)

    @property
    def serial_number(self) -> str:
        """Get serial number of device"""
        return self._data.get("SerialNumber", TEXT_UNKNOWN)


class _WiserSchedule(object):
    """Class representing a wiser Schedule"""

    def __init__(self, schedule_type: str, schedule_data: dict):
        self._type = schedule_type
        self._schedule_data = schedule_data

    def _remove_schedule_elements(self, schedule_data: dict):
        remove_list = ["id", "CurrentSetpoint", "CurrentState", "Name", "Next"]
        for item in remove_list:
            if item in schedule_data:
                del schedule_data[item]
        return schedule_data

    def _convert_from_wiser_schedule(self, schedule_data: dict):
        """
        Convert from wiser format to format suitable for yaml output
        param: scheduleData
        param: mode
        """
        # Create dict to take converted data
        schedule_output = {
            "Name": self.name,
            "Description": self._type + " schedule for " + self.name,
            "Type": self._type,
        }
        # Iterate through each day
        try:
            for day, sched in schedule_data.items():
                if day.title() in (WEEKDAYS + WEEKENDS + SPECIAL_DAYS):
                    schedule_set_points = self._convert_wiser_to_yaml_day(
                        sched, self._type
                    )
                    schedule_output.update({day.capitalize(): schedule_set_points})
            return schedule_output
        except Exception:
            return None

    def _convert_to_wiser_schedule(self, schedule_yaml_data: dict):
        """
        Convert from wiser format to format suitable for yaml output
        param: scheduleData
        param: mode
        """
        schedule_output = {}
        try:
            for day, sched in schedule_yaml_data.items():
                if day.title() in (WEEKDAYS + WEEKENDS + SPECIAL_DAYS):
                    schedule_day = self._convert_yaml_to_wiser_day(sched, self._type)
                    # If using spec days, convert to one entry for each weekday
                    if day.title() in SPECIAL_DAYS:
                        if day.title() == TEXT_WEEKDAYS:
                            for weekday in WEEKDAYS:
                                schedule_output.update({weekday: schedule_day})
                        if day.title() == TEXT_WEEKENDS:
                            for weekend_day in WEEKENDS:
                                schedule_output.update({weekend_day: schedule_day})
                    else:
                        schedule_output.update({day: schedule_day})
            return schedule_output
        except Exception:
            return None

    def _convert_wiser_to_yaml_day(self, day_schedule, schedule_type):
        """
        Convert from wiser schedule format to format for yaml output.
        param daySchedule: json schedule for a day in wiser v2 format
        param scheduleType: Heating or OnOff
        return: json
        """
        schedule_set_points = []
        if schedule_type == TEXT_HEATING:
            for i in range(len(day_schedule[TEXT_TIME])):
                schedule_set_points.append(
                    {
                        TEXT_TIME: (
                            datetime.strptime(
                                format(day_schedule[TEXT_TIME][i], "04d"), "%H%M"
                            )
                        ).strftime("%H:%M"),
                        TEXT_TEMP: _from_wiser_temp(day_schedule[TEXT_DEGREESC][i]),
                    }
                )
        else:
            for i in range(len(day_schedule)):
                schedule_set_points.append(
                    {
                        TEXT_TIME: (
                            datetime.strptime(
                                format(abs(day_schedule[i]), "04d"), "%H%M"
                            )
                        ).strftime("%H:%M"),
                        TEXT_STATE: TEXT_ON if day_schedule[i] > 0 else TEXT_OFF,
                    }
                )
        return schedule_set_points

    def _convert_yaml_to_wiser_day(self, day_schedule, schedule_type):
        """
        Convert from yaml format to wiser v2 schedule format.
        param daySchedule: json schedule for a day in yaml format
        param scheduleType: Heating or OnOff
        return: json
        """
        times = []
        temps = []

        if schedule_type == TEXT_HEATING:
            for item in day_schedule:
                for key, value in item.items():
                    if key.title() == TEXT_TIME:
                        time = str(value).replace(":", "")
                        times.append(time)
                    if key.title() == TEXT_TEMP:
                        temp = _to_wiser_temp(
                            value if str(value).title() != TEXT_OFF else TEMP_OFF
                        )
                        temps.append(temp)
            return {TEXT_TIME: times, TEXT_DEGREESC: temps}
        else:
            for entry in day_schedule:
                try:
                    time = int(str(entry.get("Time")).replace(":", ""))
                    if entry.get("State").title() == TEXT_OFF:
                        time = 0 - int(time)
                except Exception as ex:
                    _LOGGER.debug(ex)
                    time = 0
                times.append(time)
            return times

    def _send_schedule(self, schedule_data: dict, id: int = 0) -> bool:
        """
        Send system control command to Wiser Hub
        param cmd: json command structure
        return: boolen - true = success, false = failed
        """
        try:
            rest = _WiserRestController()
            result = rest._send_schedule(
                WISERHUBSCHEDULES
                + "{}/{}".format(self._type, str(id if id != 0 else self.id)),
                schedule_data,
            )
            if result:
                _LOGGER.info(
                    "Wiser schedule - {} command successful".format(
                        inspect.stack()[1].function
                    )
                )
            return result
        except Exception as ex:
            _LOGGER.debug(ex)

    # TODO: Decide on seperate properties or single setting or both
    @property
    def current_target_temperature(self) -> float:
        """Get current scheduled target temperature for heating device"""
        return _from_wiser_temp(
            self._schedule_data.get("CurrentSetpoint", TEMP_MINIMUM)
        )

    @property
    def current_setting(self):
        """Get current scheduled setting (temp or state)"""
        if self._type == "Heating":
            return self.current_target_temperature
        if self._type == "OnOff":
            return self.current_state

    @property
    def current_state(self) -> str:
        """Get current scheduled state for on off device"""
        return self._schedule_data.get("CurrentState", TEXT_UNKNOWN)

    @property
    def id(self) -> int:
        """Get id of schedule"""
        return self._schedule_data.get("id")

    @property
    def name(self) -> str:
        """Get name of schedule"""
        return self._schedule_data.get("Name")

    @property
    def next_entry(self):
        """Get details of next schedule entry"""
        return _WiserScheduleNext(self._type, self._schedule_data.get("Next"))

    @property
    def schedule_data(self) -> str:
        """Get json output of schedule data"""
        return self._remove_schedule_elements(self._schedule_data.copy())

    @property
    def schedule_type(self) -> str:
        """Get schedule type (heating or on/off)"""
        return self._type

    def copy_schedule(self, to_id: int) -> bool:
        """
        Copy this schedule to another schedule
        param toId: id of schedule to copy to
        return: boolen - true = successfully set, false = failed to set
        """
        return self._send_schedule(self._schedule_data, to_id)

    def save_schedule_to_file(self, schedule_file: str) -> bool:
        """
        Save this schedule to a file as json.
        param scheduleFile: file to write schedule to
        return: boolen - true = successfully saved, false = failed to save
        """
        try:
            with open(schedule_file, "w") as file:
                json.dump(self._schedule_data, file, indent=4)
            return True
        except Exception as ex:
            _LOGGER.debug(ex)
            return False

    def save_schedule_to_yaml_file(self, schedule_yaml_file: str) -> bool:
        """
        Save this schedule to a file as yaml.
        param scheduleFile: file to write schedule to
        return: boolen - true = successfully saved, false = failed to save
        """
        try:
            yaml = YAML()
            with open(schedule_yaml_file, "w") as file:
                yaml.dump(self._convert_from_wiser_schedule(self._schedule_data), file)
            return True
        except Exception as ex:
            _LOGGER.debug(ex)
            return False

    def set_schedule(self, schedule_data: dict) -> bool:
        """
        Set new schedule
        param scheduleData: json data respresenting a schedule
        return: boolen - true = successfully set, false = failed to set
        """
        return self._send_schedule(self._remove_schedule_elements(schedule_data))

    def set_schedule_from_file(self, schedule_file: str):
        """
        Set schedule from file.
        param schedule_file: file of json data respresenting a schedule
        return: boolen - true = successfully set, false = failed to set
        """
        try:
            with open(schedule_file, "r") as file:
                self.set_schedule(self._remove_schedule_elements(json.load(file)))
                return True
        except Exception as ex:
            _LOGGER.debug(ex)
            return False

    def set_schedule_from_yaml_file(self, schedule_file: str) -> bool:
        """
        Set schedule from file.
        param schedule_file: file of yaml data respresenting a schedule
        return: boolen - true = successfully set, false = failed to set
        """
        try:
            yaml = YAML()
            with open(schedule_file, "r") as file:
                y = yaml.load(file)
                self.set_schedule(self._convert_to_wiser_schedule(y))
                return True
        except Exception as ex:
            _LOGGER.debug(ex)
            return False


class _WiserSystem(object):
    """Class representing a Wiser Hub device"""

    def __init__(
        self, data: dict, device_data: dict, network_data: dict, cloud_data: dict
    ):
        self._data = data
        self._device_data = device_data
        self._network_data = network_data
        self._cloud_data = cloud_data

        self._automatic_daylight_saving = data.get("AutomaticDaylightSaving")
        self._away_mode_affects_hotwater = data.get("AwayModeAffectsHotWater")
        self._away_mode_target_temperature = data.get("AwayModeSetPointLimit")
        self._comfort_mode_enabled = data.get("ComfortModeEnabled")
        self._degraded_mode_target_temperature = data.get(
            "DegradedModeSetpointThreshold"
        )
        self._eco_mode_enabled = data.get("EcoModeEnabled")
        self._hub_time = datetime.fromtimestamp(data.get("UnixTime"))
        self._override_type = data.get("OverrideType", "")
        self._timezone_offset = data.get("TimeZoneOffset")
        self._valve_protection_enabled = data.get("ValveProtectionEnabled")

    def _send_command(self, cmd: dict) -> bool:
        """
        Send system control command to Wiser Hub
        param cmd: json command structure
        return: boolen - true = success, false = failed
        """
        rest = _WiserRestController()
        result = rest._send_command(WISERSYSTEM, cmd)
        if result:
            _LOGGER.info(
                "Wiser hub - {} command successful".format(inspect.stack()[1].function)
            )
        return result

    @property
    def active_firmware_version(self) -> str:
        """Get current hub firmware version"""
        return self._data.get("ActiveSystemVersion", TEXT_UNKNOWN)

    @property
    def automatic_daylight_saving_enabled(self) -> bool:
        """Get or set if auto daylight saving is enabled"""
        return self._automatic_daylight_saving

    @automatic_daylight_saving_enabled.setter
    def automatic_daylight_saving_enabled(self, enabled: bool):
        if self._send_command({"AutomaticDaylightSaving": str(enabled).lower()}):
            self._automatic_daylight_saving = enabled

    @property
    def away_mode_enabled(self) -> bool:
        """Get or set if away mode is enabled"""
        return True if self._override_type == "Away" else False

    @away_mode_enabled.setter
    def away_mode_enabled(self, enabled: bool):
        if self._send_command({"RequestOverride": {"Type": 2 if enabled else 0}}):
            self._override_type = "Away" if enabled else ""

    @property
    def away_mode_affects_hotwater(self) -> bool:
        """Get or set if setting away mode affects hot water"""
        return self._away_mode_affects_hotwater

    @away_mode_affects_hotwater.setter
    def away_mode_affects_hotwater(self, enabled: bool = False):
        if self._send_command({"AwayModeAffectsHotWater": str(enabled).lower()}):
            self._away_mode_affects_hotwater = enabled

    @property
    def away_mode_target_temperature(self) -> float:
        """Get or set target temperature for away mode"""
        return _from_wiser_temp(self._away_mode_target_temperature)

    @away_mode_target_temperature.setter
    def away_mode_target_temperature(self, temp: float):
        temp = _to_wiser_temp(temp)
        if self._send_command({"AwayModeSetPointLimit": temp}):
            self._away_mode_target_temperature = _to_wiser_temp(temp)

    @property
    def boiler_fuel_type(self) -> str:
        """Get boiler fuel type setting"""
        # TODO: Add ability to set to 1 of 3 types
        return self._data.get("BoilerSettings", {"FuelType": TEXT_UNKNOWN}).get(
            "FuelType"
        )

    @property
    def brand_name(self) -> str:
        """Get brand name of Wiser hub"""
        return self._data.get("BrandName")

    @property
    def cloud(self):
        """Get cloud settings"""
        return _WiserCloud(self._data.get("CloudConnectionStatus"), self._cloud_data)

    @property
    def comfort_mode_enabled(self) -> bool:
        """Get or set if comfort mode is enabled"""
        return self._comfort_mode_enabled

    @comfort_mode_enabled.setter
    def comfort_mode_enabled(self, enabled: bool):
        if self._send_command({"ComfortModeEnabled": enabled}):
            self._comfort_mode_enabled = enabled

    @property
    def degraded_mode_target_temperature(self) -> float:
        """Get or set degraded mode target temperature"""
        return _from_wiser_temp(self._degraded_mode_target_temperature)

    @degraded_mode_target_temperature.setter
    def degraded_mode_target_temperature(self, temp: float):
        temp = _to_wiser_temp(temp)
        if self._send_command({"DegradedModeSetpointThreshold": temp}):
            self._degraded_mode_target_temperature = temp

    @property
    def eco_mode_enabled(self) -> bool:
        """Get or set whether eco mode is enabled"""
        return self._eco_mode_enabled

    @eco_mode_enabled.setter
    def eco_mode_enabled(self, enabled: bool):
        if self._send_command({"EcoModeEnabled": enabled}):
            self._eco_mode_enabled = enabled

    @property
    def firmware_over_the_air_enabled(self) -> bool:
        """Whether firmware updates over the air are enabled on the hub"""
        return self._data.get("FotaEnabled")

    @property
    def geo_position(self):
        """Get geo location information"""
        return _WiserGPS(self._data.get("GeoPosition", {}))

    @property
    def heating_button_override_state(self) -> bool:
        """Get if heating override button is on"""
        return (
            True if self._data.get("HeatingButtonOverrideState") == TEXT_ON else False
        )

    @property
    def hotwater_button_override_state(self) -> bool:
        """Get if hot water override button is on"""
        return (
            True if self._data.get("HotWaterButtonOverrideState") == TEXT_ON else False
        )

    @property
    def hub_time(self) -> datetime:
        """Get the current time on hub"""
        return self._hub_time

    @property
    def name(self) -> str:
        """Get name of hub"""
        return self._network_data.get("Station", {"MdnsHostname": TEXT_UNKNOWN}).get(
            "MdnsHostname"
        )

    @property
    def network(self):
        """Get network information from hub"""
        return _WiserNetwork(self._network_data.get("Station", {}))

    @property
    def opentherm_connection_status(self) -> str:
        """Get opentherm connection status"""
        return self._data.get("OpenThermConnectionStatus", TEXT_UNKNOWN)

    @property
    def pairing_status(self) -> str:
        """Get account pairing status"""
        return self._data.get("PairingStatus", TEXT_UNKNOWN)

    @property
    def system_mode(self) -> str:
        """Get current system mode"""
        return self._data.get("SystemMode", TEXT_UNKNOWN)

    @property
    def timezone_offset(self) -> int:
        """Get timezone offset in minutes"""
        return self._timezone_offset

    @timezone_offset.setter
    def timezone_offset(self, offset: int):
        if self._send_command({"TimeZoneOffset": offset}):
            self._timezone_offset = offset

    @property
    def user_overrides_active(self) -> bool:
        """Get if any overrides are active"""
        return self._data.get("UserOverridesActive", False)

    @property
    def valve_protection_enabled(self) -> bool:
        """Get or set if valve protection is enabled"""
        return self._valve_protection_enabled

    @valve_protection_enabled.setter
    def valve_protection_enabled(self, enabled: bool):
        """
        Set the valve protection setting on the wiser hub
        param enabled: turn on or off
        """
        if self._send_command({"ValveProtectionEnabled": enabled}):
            self._valve_protection_enabled = enabled

    def boost_all_rooms(self, inc_temp: float, duration: int) -> bool:
        """
        Boost the temperature of all rooms
        param inc_temp: increase target temperature over current temperature by 0C to 5C
        param duration: the duration to boost the room temperatures in minutes
        return: boolean
        """
        return self._send_command(
            {
                "RequestOverride": {
                    "Type": "Boost",
                    "DurationMinutes": duration,
                    "IncreaseSetPointBy": _to_wiser_temp(inc_temp)
                    if _to_wiser_temp(inc_temp) <= MAX_BOOST_INCREASE
                    else MAX_BOOST_INCREASE,
                }
            }
        )

    def cancel_all_overrides(self):
        """
        Cancel all overrides and set room schedule to the current temperature setting for the mode
        return: boolean
        """
        return self._send_command({"RequestOverride": {"Type": "CancelUserOverrides"}})

    


class _WiserSmartValve(_WiserDevice):
    """Class representing a Wiser Smart Valve device"""

    def __init__(self, data: dict, device_type_data: dict):
        super().__init__(data)
        self._data = data
        self._device_type_data = device_type_data

        self._device_lock_enabled = data.get("DeviceLockEnabled", False)
        self._indentify_active = data.get("IdentifyActive", False)

    def _send_command(self, cmd: dict):
        """
        Send control command to the smart valve
        param cmd: json command structure
        return: boolen - true = success, false = failed
        """
        rest = _WiserRestController()
        result = rest._send_command(WISERSMARTVALVE.format(self.id), cmd)
        if result:
            _LOGGER.info(
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
        if self._send_command({"DeviceLockEnabled": enable}):
            self._device_lock_enabled = enable

    @property
    def current_target_temperature(self) -> float:
        """Get the smart valve current target temperature setting"""
        return _from_wiser_temp(self._device_type_data.get("SetPoint"))

    @property
    def current_temperature(self) -> float:
        """Get the current temperature measured by the smart valve"""
        return _from_wiser_temp(self._device_type_data.get("MeasuredTemperature"))

    @property
    def identify(self) -> bool:
        """Get or set if the smart valve identify function is enabled"""
        return self._indentify_active

    @identify.setter
    def identify(self, enable: bool = False):
        if self._send_command({"Identify": enable}):
            self._indentify_active = enable

    @property
    def mounting_orientation(self) -> str:
        """Get the mouting orientation of the smart valve"""
        return self._device_type_data.get("MountingOrientation")

    @property
    def percentage_demand(self) -> int:
        """Get the current percentage demand of the smart valve"""
        return self._device_type_data.get("PercentageDemand")


class _WiserRoomStat(_WiserDevice):
    """Class representing a Wiser Room Stat device"""

    def __init__(self, data, device_type_data):
        super().__init__(data)
        self._data = data
        self._device_type_data = device_type_data
        self._device_lock_enabled = data.get("DeviceLockEnabled", False)
        self._indentify_active = data.get("IdentifyActive", False)

    def _send_command(self, cmd: dict):
        """
        Send control command to the room stat
        param cmd: json command structure
        return: boolen - true = success, false = failed
        """
        rest = _WiserRestController()
        result = rest._send_command(WISERROOMSTAT.format(self.id), cmd)
        if result:
            _LOGGER.info(
                "Wiser room stat - {} command successful".format(
                    inspect.stack()[1].function
                )
            )
        return result

    @property
    def battery(self):
        """Get the battery information for the room stat"""
        return _WiserBattery(self._data)

    @property
    def current_humidity(self) -> int:
        """Get the current humidity reading of the room stat"""
        return self._device_type_data.get("MeasuredHumidity", 0)

    @property
    def current_target_temperature(self) -> float:
        """Get the room stat current target temperature setting"""
        return _from_wiser_temp(self._device_type_data.get("SetPoint", 0))

    @property
    def current_temperature(self) -> float:
        """Get the current temperature measured by the room stat"""
        return _from_wiser_temp(self._device_type_data.get("MeasuredTemperature", 0))

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
        return self._send_command({"DeviceLockEnabled": enable})

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
        if self._send_command({"Identify": enable}):
            self._indentify_active = enable


class _WiserSmartPlug(_WiserDevice):
    """Class representing a Wiser Smart Plug device"""

    def __init__(self, data: dict, device_type_data: dict, schedule: _WiserSchedule):
        super().__init__(data)
        self._data = data
        self._device_type_data = device_type_data
        self._schedule = schedule

        self._away_action = device_type_data.get("AwayAction", TEXT_UNKNOWN)
        self._mode = device_type_data.get("Mode", TEXT_UNKNOWN)
        self._name = device_type_data.get("Name", TEXT_UNKNOWN)
        self._output_state = device_type_data.get("OutputState", TEXT_OFF)

    def _send_command(self, cmd: dict):
        """
        Send control command to the smart plug
        param cmd: json command structure
        return: boolen - true = success, false = failed
        """
        rest = _WiserRestController()
        result = rest._send_command(WISERSMARTPLUG.format(self.id), cmd)
        if result:
            _LOGGER.info(
                "Wiser smart plug - {} command successful".format(
                    inspect.stack()[1].function
                )
            )
        return result

    @property
    def away_action(self) -> str:
        """Get or set the away action of the smart plug (off or no change)"""
        return self._away_action

    @away_action.setter
    def away_action(self, action: WiserAwayActionEnum):
        result = self._send_command({"AwayAction": action.value})
        if result:
            self._away_action = action.value

    @property
    def control_source(self) -> str:
        """Get the current control source of the smart plug"""
        return self._device_type_data.get("ControlSource", TEXT_UNKNOWN)

    @property
    def manual_state(self) -> str:
        """Get the current manual mode setting of the smart plug"""
        return self._device_type_data.get("ManualState", TEXT_UNKNOWN)

    @property
    def mode(self) -> str:
        """Get or set the current mode of the smart plug (Manual or Auto)"""
        return self._mode

    @mode.setter
    def mode(self, mode: WiserModeEnum):
        if mode == WiserModeEnum.off:
            raise ValueError("You cannot set a smart plug to off mode.")
        else:
            if self._send_command({"Mode": mode.value}):
                self._mode = mode

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
            self._output_is_on = True
        return result

    def turn_off(self) -> bool:
        """
        Turn off the smart plug
        return: boolean
        """
        result = self._send_command({"RequestOutput": TEXT_OFF})
        if result:
            self._output_is_on = False
        return result


class _WiserRoom(object):
    """Class representing a Wiser Room entity"""

    def __init__(self, data: dict, schedule: _WiserSchedule, devices: _WiserDevice):
        self._data = data
        self._schedule = schedule
        self._devices = devices
        self._mode = WiserModeEnum(data.get("Mode"))
        self._name = data.get("Name")
        self._window_detection_active = data.get("WindowDetectionActive", TEXT_UNKNOWN)

    def _send_command(self, cmd: dict):
        """
        Send control command to the room
        param cmd: json command structure
        return: boolen
        """
        rest = _WiserRestController()
        result = rest._send_command(WISERROOM.format(self.id), cmd)
        if result:
            _LOGGER.info(
                "Wiser room - {} command successful".format(inspect.stack()[1].function)
            )
        return result

    @property
    def boost_end_time(self) -> datetime:
        """Get boost end timestamp"""
        return datetime.fromtimestamp(self._data.get("OverrideTimeoutUnixTime", 0))

    @property
    def boost_time_remaining(self) -> datetime:
        """Get boost time remaining"""
        if self._data.get("OverrideTimeoutUnixTime", 0) > 0:
            now = datetime.now()
            boost_end_time = datetime.fromtimestamp(
                self._data.get("OverrideTimeoutUnixTime", 0)
            )
            return boost_end_time - now
        else:
            return 0

    @property
    def current_target_temperature(self) -> float:
        """Get current target temperature for the room"""
        return _from_wiser_temp(self._data.get("CurrentSetPoint", TEMP_MINIMUM))

    @property
    def current_temperature(self) -> float:
        """Get current temperature of the room"""
        return _from_wiser_temp(self._data.get("CalculatedTemperature", TEMP_MINIMUM))

    @property
    def devices(self):
        """Get devices associated with the room"""
        return self._devices

    @property
    def id(self) -> int:
        """Get the id of the room"""
        return self._data.get("id")

    @property
    def is_boosted(self) -> bool:
        """Get if the room temperature is currently boosted"""
        return (
            True
            if self._data.get("SetpointOrigin", TEXT_UNKNOWN) == "FromBoost"
            else False
        )

    @property
    def is_heating(self) -> bool:
        """Get if the room is currently heating"""
        return (
            True if self._data.get("ControlOutputState", TEXT_OFF) == TEXT_ON else False
        )

    @property
    def manual_target_temperature(self) -> float:
        """Get current target temperature for manual mode"""
        return _from_wiser_temp(self._data.get("ManualSetPoint", TEMP_MINIMUM))

    @property
    def mode(self) -> str:
        """Get or set current mode for the room (Off, Manual, Auto)"""
        return self._mode

    @mode.setter
    def mode(self, mode: WiserModeEnum):
        if mode == WiserModeEnum.off:
            if self._send_command({"Mode": WiserModeEnum.manual.value}):
                self.set_manual_temperature(TEMP_OFF)
                self._mode = mode.value
        elif mode == WiserModeEnum.manual:
            if self._send_command({"Mode": mode.value}):
                self._mode = mode.value
                if self.current_target_temperature == TEMP_OFF:
                    self.set_manual_temperature(self.scheduled_target_temperature)
        else:
            if self._send_command({"Mode": mode.value}):
                self._mode = mode.value

    @property
    def name(self) -> str:
        """Get or set the name of the room"""
        return self._name

    @name.setter
    def name(self, name: str):
        if self._send_command({"Name": name.title()}):
            self._name = name.title()

    @property
    def override_target_temperature(self) -> float:
        """Get the override target temperature of the room"""
        return self._data.get("OverrideSetpoint", 0)

    @property
    def override_type(self) -> str:
        """Get the current override type for the room"""
        return self._data.get("OverrideType", "None")

    @property
    def percentage_demand(self) -> int:
        """Get the percentage demand of the room"""
        return self._data.get("PercentageDemand", 0)

    @property
    def schedule(self):
        """Get the schedule for the room"""
        return self._schedule

    @property
    def schedule_id(self) -> int:
        """Get the schedule id for the room"""
        return self._data.get("ScheduleId")

    @property
    def scheduled_target_temperature(self) -> float:
        """Get the scheduled target temperature for the room"""
        return _from_wiser_temp(self._data.get("ScheduledSetPoint", TEMP_MINIMUM))

    @property
    def target_temperature_origin(self) -> str:
        """Get the origin of the target temperature setting for the room"""
        return self._data.get("SetpointOrigin", TEXT_UNKNOWN)

    @property
    def window_detection_active(self) -> bool:
        """Get or set if window detection is active"""
        return self._window_detection_active

    @window_detection_active.setter
    def window_detection_active(self, enabled: bool):
        if self._send_command({"WindowDetectionActive": enabled}):
            self._window_detection_active = enabled

    @property
    def window_state(self) -> str:
        """
        Get the currently detected window state for the room.
        Window detection needs to be active
        """
        return self._data.get("WindowState", TEXT_UNKNOWN)

    def set_boost(self, inc_temp: float, duration: int) -> bool:
        """
        Boost the temperature of the room
        param inc_temp: increase target temperature over current temperature by 0C to 5C
        param duration: the duration to boost the room temperature in minutes
        return: boolean
        """
        return self._send_command(
            {
                "RequestOverride": {
                    "Type": "Boost",
                    "DurationMinutes": duration,
                    "IncreaseSetPointBy": _to_wiser_temp(inc_temp)
                    if _to_wiser_temp(inc_temp) <= MAX_BOOST_INCREASE
                    else MAX_BOOST_INCREASE,
                }
            }
        )

    def cancel_boost(self) -> bool:
        """
        Cancel the temperature boost of the room
        return: boolean
        """
        if self.is_boosted:
            return self.cancel_overrides()
        else:
            return False

    def override_temperature(self, temp: float) -> bool:
        """
        Set the temperature of the room to override current schedule temp or in manual mode
        param temp: the temperature to set in C
        return: boolean
        """
        return self._send_command(
            {
                "RequestOverride": {
                    "Type": "Manual",
                    "SetPoint": _to_wiser_temp(temp),
                }
            }
        )

    def override_temperature_for_duration(self, temp: float, duration: int) -> bool:
        """
        Set the temperature of the room to override current schedule temp or in manual mode
        param temp: the temperature to set in C
        return: boolean
        """
        return self._send_command(
            {
                "RequestOverride": {
                    "Type": "Manual",
                    "DurationMinutes": duration,
                    "SetPoint": _to_wiser_temp(temp),
                }
            }
        )

    def set_manual_temperature(self, temp: float):
        """
        Set the manual temperature for the room
        param temp: the temperature to set in C
        return: boolean
        """
        self.mode = WiserModeEnum.manual
        return self.override_temperature(temp)

    def schedule_advance(self):
        """
        Advance room schedule to the next scheduled time and temperature setting
        return: boolean
        """
        return self.override_temperature(
            _from_wiser_temp(self.schedule.next_entry.setting)
        )

    def cancel_overrides(self):
        """
        Cancel all overrides and set room schedule to the current temperature setting for the mode
        return: boolean
        """
        return self._send_command({"RequestOverride": {"Type": "None"}})


class _WiserHeating:
    """Class representing a Wiser Heating Channel"""

    def __init__(self, data: dict, rooms: dict):
        self._data = data
        self._rooms = rooms

    @property
    def demand_on_off_output(self):
        """Get the demand output for the heating channel"""
        return self._data.get("DemandOnOffOutput", TEXT_UNKNOWN)

    @property
    def heating_relay_status(self) -> str:
        """Get the state of the heating channel relay"""
        return self._data.get("HeatingRelayState", TEXT_UNKNOWN)

    @property
    def id(self) -> int:
        """Get the id of the heating channel"""
        return self._data.get("id")

    @property
    def is_smart_valve_preventing_demand(self) -> bool:
        """Get if a smart valve is preventing demand for heating channel"""
        return self._data.get("IsSmartValvePreventingDemand", False)

    @property
    def name(self) -> str:
        """Get the name of the heating channel"""
        return self._data.get("Name", TEXT_UNKNOWN)

    @property
    def percentage_demand(self) -> int:
        """Get the percentage demand of the heating channel"""
        return self._data.get("PercentageDemand", 0)

    @property
    def rooms(self):
        """Get the rooms attached to this heating channel"""
        rooms = []
        for room in self._rooms:
            if room.id in self.room_ids:
                rooms.append(room)
        return rooms

    @property
    def room_ids(self):
        """Get a list of the room ids attached to this heating channel"""
        return self._data.get("RoomIds", [])


class _WiserHotwater:
    """Class representing a Wiser Hot Water controller"""

    def __init__(self, data: dict, schedule: dict):
        self._data = data
        self._schedule = schedule
        self._mode = data.get("Mode")

    def _send_command(self, cmd: dict):
        """
        Send control command to the hot water
        param cmd: json command structure
        return: boolen - true = success, false = failed
        """
        rest = _WiserRestController()
        result = rest._send_command(WISERHOTWATER.format(self.id), cmd)
        if result:
            _LOGGER.info(
                "Wiser hot water - {} command successful".format(
                    inspect.stack()[1].function
                )
            )
        return result

    @property
    def current_control_source(self) -> str:
        """Get the current control source for the hot water"""
        return self._data.get("HotWaterDescription", TEXT_UNKNOWN)

    @property
    def current_state(self) -> str:
        """Get the current state of the hot water"""
        return self._data.get("HotWaterRelayState", TEXT_UNKNOWN)

    @property
    def id(self) -> int:
        """Get the id of the hot water channel"""
        return self._data.get("id")

    @property
    def is_heating(self) -> bool:
        """Get if the hot water is currently heating"""
        return True if self._data.get("WaterHeatingState") == TEXT_ON else False

    @property
    def is_boosted(self) -> bool:
        """Get if the hot water is currently boosted"""
        return True if self._data.get("Override") else False  # TODO: Check this

    @property
    def mode(self) -> str:
        """Get or set the current hot water mode (Manual or Auto)"""
        return self._mode

    @mode.setter
    def mode(self, mode: WiserModeEnum):
        if mode == WiserModeEnum.off:
            if self._send_command({"Mode": WiserModeEnum.manual.value}):
                self.override_state(WiserHotWaterStateEnum.off)
        else:
            if self._send_command({"Mode": mode.value}):
                self._mode = mode.value

    @property
    def schedule(self):
        """Get the hot water schedule"""
        return self._schedule

    def schedule_advance(self):
        """
        Advance hot water schedule to the next scheduled time and state setting
        return: boolean
        """
        # TODO: Fix this!
        if self.schedule.next_entry.setting == WiserHotWaterStateEnum.on.value:
            return self.override_state(WiserHotWaterStateEnum.on)
        else:
            return self.override_state(WiserHotWaterStateEnum.off)

    def override_state(self, state: WiserHotWaterStateEnum) -> bool:
        """
        Override hotwater state.  In auto this is until the next scheduled event.  In manual mode this is until changed.
        return: boolean
        """
        if state == WiserHotWaterStateEnum.on:
            return self._send_command(
                {"RequestOverride": {"Type": "Manual", "SetPoint": _to_wiser_temp(HW_ON)}}
            )
        else:
            return self._send_command(
                {"RequestOverride": {"Type": "Manual", "SetPoint": _to_wiser_temp(HW_OFF)}}
            )

    def override_state_for_duration(self, state: WiserHotWaterStateEnum, duration: int) -> bool:
        """
        Override the hot water state for x minutes, overriding the current schedule or manual setting
        param duration: the duration to turn on for in minutes
        return: boolean
        """
        if state == WiserHotWaterStateEnum.on:
            return self._send_command(
                {
                    "RequestOverride": {
                        "Type": "Manual",
                        "DurationMinutes": duration,
                        "SetPoint": _to_wiser_temp(HW_ON)
                    }
                }
            )
        else:
            return self._send_command(
                {
                    "RequestOverride": {
                        "Type": "Manual",
                        "DurationMinutes": duration,
                        "SetPoint": _to_wiser_temp(HW_OFF)
                    }
                }
            )

    def cancel_overrides(self):
        """
        Cancel all overrides of the hot water
        return: boolean
        """
        return self._send_command({"RequestOverride": {"Type": "None"}})


# -----------------------------------------------------------
# Support Classess
# -----------------------------------------------------------

class _WiserNetwork:
    """Data structure for network information for a Wiser Hub"""

    def __init__(self, data: dict):
        self._data = data
        self._dhcp_status = data.get("DhcpStatus", {})
        self._network_interface = data.get("NetworkInterface", {})

    @property
    def dhcp_mode(self) -> str:
        """Get the current dhcp mode of the hub"""
        return self._data.get("NetworkInterface", {}).get("DhcpMode", TEXT_UNKNOWN)

    @property
    def hostname(self) -> str:
        """Get the host name of the hub"""
        return self._data.get("NetworkInterface", {}).get("HostName", TEXT_UNKNOWN)

    @property
    def ip_address(self) -> str:
        """Get the ip address of the hub"""
        if self.dhcp_mode == "Client":
            return self._dhcp_status.get("IPv4Address", TEXT_UNKNOWN)
        else:
            return self._network_interface.get("IPv4HostAddress", TEXT_UNKNOWN)

    @property
    def ip_subnet_mask(self) -> str:
        """Get the subnet mask of the hub"""
        if self.dhcp_mode == "Client":
            return self._dhcp_status.get("IPv4SubnetMask", TEXT_UNKNOWN)
        else:
            return self._network_interface.get("IPv4SubnetMask", TEXT_UNKNOWN)

    @property
    def ip_gateway(self) -> str:
        """Get the default gateway of the hub"""
        if self.dhcp_mode == "Client":
            return self._dhcp_status.get("IPv4DefaultGateway", TEXT_UNKNOWN)
        else:
            return self._network_interface.get("IPv4DefaultGateway", TEXT_UNKNOWN)

    @property
    def ip_primary_dns(self) -> str:
        """Get the primary dns server of the hub"""
        if self.dhcp_mode == "Client":
            return self._dhcp_status.get("IPv4PrimaryDNS", TEXT_UNKNOWN)
        else:
            return self._network_interface.get("IPv4PrimaryDNS", TEXT_UNKNOWN)

    @property
    def ip_secondary_dns(self) -> str:
        """Get the secondary dns server of the hub"""
        if self.dhcp_mode == "Client":
            return self._dhcp_status.get("IPv4SecondaryDNS", TEXT_UNKNOWN)
        else:
            return self._network_interface.get("IPv4SecondaryDNS", TEXT_UNKNOWN)

    @property
    def mac_address(self) -> str:
        """Get the mac address of the hub wifi interface"""
        return self._data.get("MacAddress", TEXT_UNKNOWN)

    @property
    def signal_percent(self) -> int:
        """Get the wifi signal strength percentage"""
        return min(100, int(2 * (self._data.get("RSSI", {}).get("Current", 0) + 100)))

    @property
    def signal_rssi(self) -> int:
        """Get the wifi signal rssi value"""
        return self._data.get("RSSI", {}).get("Current", 0)

    @property
    def security_mode(self) -> str:
        """Get the wifi security mode"""
        return self._data.get("SecurityMode", TEXT_UNKNOWN)

    @property
    def ssid(self) -> str:
        """Get the ssid of the wifi network the hub is connected to"""
        return self._data.get("SSID", TEXT_UNKNOWN)


class _WiserCloud:
    """Data structure for cloud information for a Wiser Hub"""

    def __init__(self, cloud_status: str, data: dict):
        self._cloud_status = cloud_status
        self._data = data

    @property
    def api_host(self) -> str:
        """Get the host name of the wiser cloud"""
        return self._data.get("WiserApiHost", TEXT_UNKNOWN)

    @property
    def bootstrap_api_host(self) -> str:
        """Get the bootstrap host name of the wiser cloud"""
        return self._data.get("BootStrapApiHost", TEXT_UNKNOWN)

    @property
    def connected_to_cloud(self) -> bool:
        """Get the hub connection status to the wiser cloud"""
        return True if self._cloud_status == "Connected" else False

    @property
    def detailed_publishing_enabled(self) -> bool:
        """Get if detailed published is enabled"""
        return self._data.get("DetailedPublishing", False)

    @property
    def diagnostic_telemetry_enabled(self) -> bool:
        """Get if diagnostic telemetry is enabled"""
        return self._data.get("EnableDiagnosticTelemetry", False)

    @property
    def environment(self) -> str:
        """Get the cloud environment the hub is connected to"""
        return self._data.get("Environment", TEXT_UNKNOWN)


class _WiserBattery:
    """Data structure for battery information for a Wiser device that is powered by batteries"""

    def __init__(self, data: dict):
        self._data = data

    @property
    def level(self) -> str:
        """Get the descritpion of the battery level"""
        return self._data.get("BatteryLevel", "No Battery")

    @property
    def percent(self) -> int:
        """Get the percent of battery remaining"""
        if self._data.get("ProductType") == "RoomStat":
            return min(
                100,
                int(
                    (
                        (self.voltage - ROOMSTAT_MIN_BATTERY_LEVEL)
                        / (ROOMSTAT_FULL_BATTERY_LEVEL - ROOMSTAT_MIN_BATTERY_LEVEL)
                    )
                    * 100
                ),
            )
        elif self._data.get("ProductType") == "iTRV":
            return min(
                100,
                int(
                    (
                        (self.voltage - TRV_MIN_BATTERY_LEVEL)
                        / (TRV_FULL_BATTERY_LEVEL - TRV_MIN_BATTERY_LEVEL)
                    )
                    * 100
                ),
            )
        else:
            return 0

    @property
    def voltage(self) -> float:
        """Get the battery voltage"""
        return self._data.get("BatteryVoltage", 0) / 10


class _WiserZwaveSignal:
    """Data structure for zigbee signal information for a Wiser device"""

    def __init__(self, data: dict):
        self._data = data

    @property
    def displayed_signal_strength(self) -> str:
        """Get the description of signal strength"""
        return self._data.get("DisplayedSignalStrength", TEXT_UNKNOWN)

    @property
    def rssi(self) -> int:
        """Get the rssi (strength) of the device signal"""
        if self._data.get("ProductType") == "SmartPlug":
            return self._data.get("ReceptionOfDevice", {"Rssi": 0}).get("Rssi")
        else:
            return self._data.get("ReceptionOfController", {"Rssi": 0}).get("Rssi")

    @property
    def lqi(self) -> int:
        """Get the signal lqi (quality) for the device"""
        if self._data.get("ProductType") == "SmartPlug":
            return self._data.get("ReceptionOfDevice", {"Lqi": 0}).get("Lqi")
        else:
            return self._data.get("ReceptionOfController", {"Lqi": 0}).get("Lqi")

    @property
    def signal_strength(self) -> int:
        """Get the signal strength percent for the device"""
        return min(100, int(2 * (self.rssi + 100)))


class _WiserGPS:
    """Data structure for gps positional information for a Wiser Hub"""

    def __init__(self, data: dict):
        self._data = data

    @property
    def latitude(self) -> float:
        """Get the latitude of the hub"""
        return self._data.get("Latitude")

    @property
    def longitude(self) -> float:
        """Get the longitude of the hub"""
        return self._data.get("Longitude")


class _WiserScheduleNext:
    """Data structure for schedule next entry data"""

    def __init__(self, schedule_type: str, data: dict):
        self._schedule_type = schedule_type
        self._data = data

    @property
    def day(self) -> str:
        """Get the next entry day of the week"""
        return self._data.get("Day", "")

    @property
    def time(self) -> int:
        """Get the next entry time"""
        # TODO: convert to time
        return self._data.get("Time", 0)

    @property
    def setting(self):
        """Get the next entry setting - temp for heating, state for on/off devices"""
        if self._schedule_type == TEXT_HEATING:
            return self._data.get("DegreesC")
        if self._schedule_type == TEXT_ONOFF:
            return self._data.get("State")
        return None

# -----------------------------------------------------------
# Support Functions
# -----------------------------------------------------------
def _validate_temperature(temp: float) -> float:
    """
    Validates temperature value is in range of Wiser Hub allowed values
    Sets to min or max temp if value exceeds limits
    param temp: temperature value to validate
    return: float
    """
    if temp >= TEMP_ERROR:
        return TEMP_MINIMUM
    elif temp > TEMP_MAXIMUM:
        return TEMP_MAXIMUM
    elif temp < TEMP_MINIMUM and temp != TEMP_OFF:
        return TEMP_MINIMUM
    else:
        return temp


def _to_wiser_temp(temp: float) -> int:
    """
    Converts from degrees C to wiser hub format
    param temp: The temperature to convert
    return: Integer
    """
    # Convert to metric if imperial units set
    if _wiser_api_connection.units == WiserUnitsEmun.imperial:
        temp = _convert_from_F(temp)

    return int(_validate_temperature(temp) * 10)


def _from_wiser_temp(temp: int) -> float:
    """
    Converts from wiser hub format to degrees C
    param temp: The wiser temperature to convert
    return: Float
    """
    if temp is not None:
        if temp >= TEMP_ERROR:  # Fix high value from hub when lost sight of iTRV
            temp = TEMP_MINIMUM
        else:
            temp = round(temp / 10, 1)
    
        # Convert to imperial if imperial units set
        if _wiser_api_connection.units == WiserUnitsEmun.imperial:
            temp = _convert_to_F(temp)

        return temp
    return None

def _convert_from_F(temp: float) -> float:
    """
    Convert F temp to C
    param temp: temp in F to convert
    return: float
    """
    return round((temp - 32) * 5/9, 1)

def _convert_to_F(temp: float) -> float:
    """
    Convert C temp to F
    param temp: temp in C to convert
    return: float
    """
    return round((temp * 9/5) + 32, 1)
