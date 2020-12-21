#!/usr/bin/env python3
"""
# Wiser API Version 2

Angelosantagata@gmail.com
msparker@sky.com


https://github.com/asantaga/wiserheatingapi


This API Facade allows you to communicate with your wiserhub.
This API is used by the homeassistant integration available at
https://github.com/asantaga/wiserHomeAssistantPlatform
"""

# TODO: Allow display in F and C based on global setting
# TODO: Keep objects and update instead of recreating on hub update
# TODO: Make class that can convert to and from Unix timestamp for hub time

import enum
import json
import logging
import requests
import sys

from datetime import datetime
from ruamel.yaml import YAML
from time import sleep
from typing import cast
from zeroconf import ServiceBrowser, ServiceStateChange, Zeroconf

__VERSION__ = "2.0.0"

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
MIN_DISCOVERY_TIME = 2
MAX_DISCOVERY_TIME = 10
REST_TIMEOUT = 15
TRACEBACK_LIMIT = 3

# Text Values
TEXT_DEGREESC = "DegreesC"
TEXT_HEATING = "Heating"
TEXT_OFF = "Off"
TEXT_ON = "On"
TEXT_ONOFF = "OnOff"
TEXT_STATE = "State"
TEXT_TEMP = "Temp"
TEXT_TIME = "Time"
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


_LOGGER = logging.getLogger(__name__)

# Set traceback limit
sys.tracebacklimit = TRACEBACK_LIMIT

"""
Exception Handlers
"""


class Error(Exception):
    """Base class for exceptions in this module."""

    pass


class WiserNoDevicesFoundError(Error):
    pass


class wiserNotSupportedError(Error):
    pass


class WiserNotFoundError(Error):
    pass


class WiserNoHotWaterFoundError(Error):
    pass


class WiserNoHeatingFoundError(Error):
    pass


class WiserRESTError(Error):
    pass


class WiserHubDataNullError(Error):
    _LOGGER.info("WiserHub data null after refresh")
    pass


class WiserHubAuthenticationError(Exception):
    pass


class WiserConnectionError(Error):
    pass


class WiserHubTimeoutError(Error):
    pass


class WiserNoRoomsFoundError(Error):
    pass


class WiserNotImplementedError(Error):
    _LOGGER.info("Function not yet implemented")
    pass


# Enums


class WiserModeEnum(enum.Enum):
    off = "Off"
    auto = "Auto"
    manual = "Manual"


class WiserAwayActionEnum(enum.Enum):
    off = "Off"
    no_change = "NoChange"


class _WiserConnection:
    def __init(self):
        self.host = None
        self.secret = None
        self.hub_name = None


_wiser_api_connection = _WiserConnection()


class WiserAPI:
    """
    Main api class to access all entities and attributes of wiser system
    """

    def __init__(self, host: str, secret: str):
        self.host = host
        self.secret = secret

        # Main data stores
        self._domain_data = {}
        self._network_data = {}
        self._schedule_data = {}

        # Data stores for exposed properties
        self._schedules = []
        self._hub = None
        self._devices = []
        self._smart_valves = []
        self._smart_plugs = []
        self._room_stats = []
        self._rooms = []
        self._hotwater = None
        self._heating = []

        _LOGGER.info("WiserHub API Initialised : Version {}".format(__VERSION__))

        # Set hub secret to global object
        _wiser_api_connection.secret = self.secret

        # Do hub discovery if null IP is passed when initialised
        if self.host is None:
            wiser_discover = WiserDiscovery()
            hub = wiser_discover.discover_hub()
            if len(hub) > 0:
                _wiser_api_connection.hubName = hub[0]["name"]
                _wiser_api_connection.host = hub[0]["hostname"]

                _LOGGER.info(
                    "Hub: {}, IP: {}".format(
                        _wiser_api_connection.hubName, _wiser_api_connection.host
                    )
                )
            else:
                _LOGGER.error("No Wiser hub discovered on network")
        else:
            _wiser_api_connection.host = self.host

        # Read hub data if hub IP and secret exist
        if (
            _wiser_api_connection.host is not None
            and _wiser_api_connection.secret is not None
        ):
            self.read_hub_data()
            # TODO - Add validation fn to check for no devs, rooms etc
        else:
            _LOGGER.error("No connection info")

    @property
    def hub(self):
        return self._hub

    @property
    def devices(self):
        return self._devices

    @property
    def schedules(self):
        return self._schedules

    @property
    def smart_valves(self):
        return self._smart_valves

    @property
    def smart_plugs(self):
        return self._smart_plugs

    @property
    def room_stats(self):
        return self._room_stats

    @property
    def rooms(self):
        return self._rooms

    @property
    def hotwater(self):
        return self._hotwater

    @property
    def heating(self):
        return self._heating

    def read_hub_data(
        self, domain: bool = True, network: bool = True, schedule: bool = True
    ):
        """ Read all data from hub and populate objects """
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
        self._hub = None
        self._smart_valves = []
        self._room_stats = []
        self._smart_plugs = []

        if self._domain_data.get("Device"):
            for device in self._domain_data.get("Device"):

                # Add to generic device list
                self._devices.append(_WiserDevice(device))

                # Add device to specific device type
                if device.get("ProductType") == "Controller":
                    self._hub = _WiserHub(
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
        if self._domain_data.get("Room"):
            self._rooms = [
                _WiserRoom(
                    room,
                    self.get_schedule_by_id(room.get("ScheduleId")),
                    [
                        device
                        for device in self.devices
                        if (
                            device.id in room.get("SmartValveIds", ["0"])
                            or device.id == room.get("RoomStatId", "0")
                        )
                    ],
                )
                for room in self._domain_data.get("Room")
            ]

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
        self._heating = []
        if self._domain_data.get("HeatingChannel"):
            for heat_channel in self._domain_data.get("HeatingChannel", []):
                self._heating.append(_WiserHeating(heat_channel, self.rooms))

        # If gets here with no exceptions then success and return true
        return True

    """
    Find entities by id or name
    """
    # Rooms
    def get_room_by_id(self, id: int):
        """
        Gets a room object from the rooms id
        param id: id of room
        return: _wiserRoom object
        """
        try:
            return [room for room in self.rooms if room.id == id][0]
        except IndexError:
            return None

    def get_room_by_name(self, name: str):
        """
        Gets a room object from the rooms name
        param name: name of room
        return: _wiserRoom object
        """
        try:
            return [room for room in self.rooms if room.name == name][0]
        except IndexError:
            return None

    # Schedules
    def get_schedule_by_id(self, id: int):
        """
        Gets a schedule object from the schedules id
        param id: id of schedule
        return: _wiserSchedule object
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
        return: _wiserSchedule object
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
        return: _wiserDevice object
        """
        try:
            return [device for device in self.devices if device.id == id][0]
        except IndexError:
            return None

    def get_device_by_node_id(self, node_id: int):
        """
        Gets a device object from the devices zigbee node id
        param nodeId: zigbee node id of device
        return: _wiserDevice object
        """
        try:
            return [device for device in self.devices if device.node_id == node_id][0]
        except IndexError:
            return None

    # Smartvalves
    def get_smart_valve_by_id(self, id: int):
        """
        Gets a SmartValve object from the SmartValves id
        param id: id of smart valve
        return: _wiserSmartValve object
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
        return: _wiserSmartPlug object
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
        return: _wiserRoomStat object
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
            resp = requests.get(
                url,
                headers=self._getHeaders(),
                timeout=REST_TIMEOUT,
            )
            resp.raise_for_status()

        except requests.Timeout:
            raise WiserHubTimeoutError(
                "Connection timed out trying to update from Wiser Hub"
            )

        except requests.HTTPError as ex:
            if ex.response.status_code == 401:
                raise WiserHubAuthenticationError(
                    "Error authenticating to Wiser Hub.  Check your secret key"
                )
            elif ex.response.status_code == 404:
                raise WiserRESTError("Rest endpoint not found on Wiser Hub")
            else:
                raise WiserRESTError(
                    "Unknown error getting data from Wiser Hub.  Error is: {}".format(
                        ex.response.status_code
                    )
                )

        except requests.ConnectionError:
            raise WiserConnectionError(
                "Connection error trying to update from Wiser Hub"
            )

        return resp.json()

    def _patch_hub_data(self, url: str, patch_data: dict):
        """
        Send patch update to hub and raise errors if fails
        param url: url of hub rest api endpoint
        param patchData: json object containing command and values to set
        return: boolean
        """
        _LOGGER.debug("patchdata {} ".format(patch_data))
        response = requests.patch(
            url=url,
            headers=self._getHeaders(),
            json=patch_data,
            timeout=REST_TIMEOUT,
        )
        # TODO: Improve error handling (maybe inc retry?)
        if response.status_code != 200:
            _LOGGER.debug(
                "Set {} Response code = {}".format(patch_data, response.status_code)
            )
            raise WiserRESTError(
                "Error setting {} , error {} {}".format(
                    patch_data, response.status_code, response.text
                )
            )
        else:
            return True

    def _send_command(self, url: str, command_data: dict):
        """
        Send control command to hub and raise errors if fails
        param url: url of hub rest api endpoint
        param patchData: json object containing command and values to set
        return: boolean
        """
        url = WISERHUBDOMAIN.format(_wiser_api_connection.host) + url
        return self._patch_hub_data(url, command_data)

    def _send_schedule(self, url: str, schedule_data: dict):
        """
        Send schedule to hub and raise errors if fails
        param url: url of hub rest api endpoint
        param patchData: json object containing command and values to set
        return: boolean
        """
        url = url.format(_wiser_api_connection.host)
        return self._patch_hub_data(url, schedule_data)


class WiserDiscovery:
    """ Class to handle mDns discovery of a wiser hub on local network """

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

    def discover_hub(self):
        """
        Call zeroconf service browser until hub found or timeout
        return: boolean - true = hub found, false = hub not found
        """
        timeout = 0

        zeroconf = Zeroconf()
        services = ["_http._tcp.local."]
        ServiceBrowser(
            zeroconf, services, handlers=[self._zeroconf_on_service_state_change]
        )

        while (
            len(self._discovered_hubs) < 1 or timeout < MIN_DISCOVERY_TIME * 10
        ) and timeout < MAX_DISCOVERY_TIME * 10:
            sleep(0.1)
            timeout += 1

        zeroconf.close()
        return self._discovered_hubs


class _WiserDevice(object):
    """ Class representing a wiser device """

    def __init__(self, data: dict):
        self._data = data
        self.signal = _WiserSignal(data)

    @property
    def firmware_version(self):
        return self._data.get("ActiveFirmwareVersion", "Unknown")

    @property
    def id(self):
        return self._data.get("id")

    @property
    def model(self):
        return self._data.get("ModelIdentifier", "Unknown")

    @property
    def node_id(self):
        return self._data.get("NodeId", 0)

    @property
    def parent_node_id(self):
        return self._data.get("ParentNodeId", 0)

    @property
    def product_type(self):
        return self._data.get("ProductType", "Unknown")

    @property
    def serial_number(self):
        return self._data.get("SerialNumber", "Unknown")


class _WiserSchedule(object):
    """
    Class representing a wiser Schedule
    """

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
                            _validate_temperature(
                                value if str(value).title() != TEXT_OFF else TEMP_OFF
                            )
                        )
                        temps.append(temp)
            return {TEXT_TIME: times, TEXT_DEGREESC: temps}
        else:
            for time, state in day_schedule:
                try:
                    time = int(str(time).replace(":", ""))
                    if state.title() == TEXT_OFF:
                        time = 0 - int(time)
                except Exception:
                    time = 0
                times.append(time)
            return times

    def _send_schedule(self, schedule_data: dict, id: int = 0) -> bool:
        """
        Send system control command to Wiser Hub
        param cmd: json command structure
        return: boolen - true = success, false = failed
        """
        if id == 0:
            id = self.id
        rest = _WiserRestController()
        return rest._send_schedule(
            WISERHUBSCHEDULES + "/{}/{}".format(self._type, id), schedule_data
        )

    # TODO: Decide on seperate properties or single setting or both
    @property
    def current_target_temperature(self):
        return _from_wiser_temp(self._schedule_data.get("CurrentSetpoint"))

    @property
    def current_state(self):
        return self._schedule_data.get("CurrentState", "Unknown")

    @property
    def current_setting(self):
        if self._type == "Heating":
            return _from_wiser_temp(
                self._schedule_data.get("CurrentSetpoint", TEMP_MINIMUM)
            )
        if self._type == "OnOff":
            return self._schedule_data.get("CurrentState", "Unknown")

    @property
    def id(self):
        return self._schedule_data.get("id")

    @property
    def name(self):
        return self._schedule_data.get("Name")

    @property
    def next_entry(self):
        return _WiserScheduleNext(self._type, self._schedule_data.get("Next"))

    @property
    def schedule_data(self):
        return self._remove_schedule_elements(self._schedule_data)

    def copy_schedule(self, to_id: int):
        """
        Copy this schedule to another schedule
        param toId: id of schedule to copy to
        return: boolen - true = successfully set, false = failed to set
        """
        return self._send_schedule(self.schedule_data, to_id)

    def save_schedule_to_file(self, schedule_file: str):
        """
        Save this schedule to a file as json.
        param scheduleFile: file to write schedule to
        return: boolen - true = successfully saved, false = failed to save
        """
        try:
            with open(schedule_file, "w") as file:
                json.dump(self.schedule_data, file)
            return True
        except Exception:
            return False

    def save_schedule_to_yaml_file(self, schedule_yaml_file: str):
        """
        Save this schedule to a file as yaml.
        param scheduleFile: file to write schedule to
        return: boolen - true = successfully saved, false = failed to save
        """
        try:
            yaml = YAML()
            with open(schedule_yaml_file, "w") as file:
                yaml.dump(self._convert_from_wiser_schedule(self.schedule_data), file)
            return True
        except Exception:
            return False

    def set_schedule(self, schedule_data: dict):
        """
        Set new schedule
        param scheduleData: json data respresenting a schedule
        return: boolen - true = successfully set, false = failed to set
        """
        return self._send_schedule(schedule_data)

    def set_schedule_from_file(self, schedule_file: str):
        """
        Set schedule from file.
        param schedule_file: file of json data respresenting a schedule
        return: boolen - true = successfully set, false = failed to set
        """
        try:
            with open(schedule_file, "r") as file:
                self.set_schedule(json.load(file))
                return True
        except Exception:
            return False

    def set_schedule_from_yaml_file(self, schedule_file: str):
        """
        Set schedule from file.
        param schedule_file: file of yaml data respresenting a schedule
        return: boolen - true = successfully set, false = failed to set
        """
        try:
            yaml = YAML(typ="safe", pure=True)
            with open(schedule_file, "r") as file:
                y = yaml.load(file)
                self.set_schedule(self._convert_to_wiser_schedule(y))
                return True
        except Exception:
            return False


class _WiserHub(object):
    """ Class representing a Wiser Hub device """

    def __init__(
        self, data: dict, device_data: dict, network_data: dict, cloud_data: dict
    ):
        self._data = data
        self._device_data = device_data
        self._network_data = network_data
        self._cloud_data = cloud_data

        self._automatic_daylight_saving = data.get("AutomaticDaylightSaving")
        self._away_mode_affects_hotwater = data.get("AwayModeAffectsHotWater", False)
        self._away_mode_target_temperature = data.get("AwayModeSetPointLimit", 0)
        self._comfort_mode_enabled = data.get("ComfortModeEnabled", False)
        self._degraded_mode_target_temperature = data.get(
            "DegradedModeSetpointThreshold", 0
        )
        self._eco_mode_enabled = data.get("EcoModeEnabled", False)
        self._hub_time = data.get("UnixTime")
        self._override_type = data.get("OverrideType", "")
        self._timezone_offset = data.get("TimeZoneOffset")
        self._valve_protection_enabled = data.get("ValveProtectionEnabled", False)

    def _sendCommand(self, cmd: dict) -> bool:
        """
        Send system control command to Wiser Hub
        param cmd: json command structure
        return: boolen - true = success, false = failed
        """
        rest = _WiserRestController()
        return rest._send_command(WISERSYSTEM, cmd)

    @property
    def active_firmware_version(self):
        return self._data.get("ActiveSystemVersion")

    @property
    def automatic_daylight_saving(self):
        return self._automatic_daylight_saving

    @automatic_daylight_saving.setter
    def automatic_daylight_saving(self, enabled: bool):
        if self._sendCommand({"AutomaticDaylightSaving": str(enabled).lower()}):
            self._automatic_daylight_saving = enabled

    @property
    def away_mode(self):
        return True if self._override_type == "Away" else False

    @away_mode.setter
    def away_mode(self, enabled: bool):
        if self._sendCommand({"RequestOverride": {"Type": 2 if enabled else 0}}):
            self._override_type = "Away" if enabled else ""

    @property
    def away_mode_affects_hotwater(self):
        """
        Get the away mode affects hot water setting on the wiser hub
        """
        return self._away_mode_affects_hotwater

    @away_mode_affects_hotwater.setter
    def away_mode_affects_hotwater(self, enabled: bool = False):
        """
        Set the away mode affects hot water setting on the wiser hub
        param enabled: turn on or off
        """
        if self._sendCommand({"AwayModeAffectsHotWater": str(enabled).lower()}):
            self._away_mode_affects_hotwater = enabled

    @property
    def away_mode_target_temperature(self):
        return _from_wiser_temp(self._away_mode_target_temperature)

    @away_mode_target_temperature.setter
    def away_mode_target_temperature(self, temp: float):
        """
        Set the away mode target temperature on the wiser hub
        param temp: the temperature in C
        """
        temp = _to_wiser_temp(_validate_temperature(temp))
        if self._sendCommand({"AwayModeSetPointLimit": temp}):
            self._away_mode_target_temperature = _to_wiser_temp(temp)

    @property
    def boiler_fuel_type(self):
        return self._data.get("BoilerSettings", {"FuelType": "Unknown"}).get("FuelType")

    @property
    def brand_name(self):
        return self._data.get("BrandName")

    @property
    def cloud(self):
        return _WiserCloud(self._data.get("CloudConnectionStatus"), self._cloud_data)

    @property
    def comfort_mode(self):
        return self._comfort_mode_enabled

    @comfort_mode.setter
    def comfort_mode(self, enabled: bool):
        """
        Set the comfort setting on the wiser hub
        param enabled: turn on or off
        """
        if self._sendCommand({"ComfortModeEnabled": enabled}):
            self._comfort_mode_enabled = enabled

    @property
    def degraded_mode_target_temperature(self):
        return self._degraded_mode_target_temperature

    @degraded_mode_target_temperature.setter
    def degraded_mode_target_temperature(self, temp: float):
        """
        Set the degraded mode target temperature on the wiser hub
        param temp: the temperature in degrees C
        """
        temp = _to_wiser_temp(_validate_temperature(temp))
        if self._sendCommand({"DegradedModeSetpointThreshold": temp}):
            self._degraded_mode_target_temperature = temp

    @property
    def eco_mode(self):
        return self._eco_mode_enabled

    @eco_mode.setter
    def eco_mode(self, enabled: bool):
        """
        Set the eco mode setting on the wiser hub
        param enabled: turn on or off
        """
        if self._sendCommand({"EcoModeEnabled": enabled}):
            self._eco_mode_enabled = enabled

    @property
    def firmware_over_the_air(self):
        return self._data.get("FotaEnabled")

    @property
    def geo_position(self):
        return _WiserGPS(self._data.get("GeoPosition", {}))

    @property
    def heating_button_override_state(self):
        return True if self._data.get("HeatingButtonOverrideState") == "On" else False

    @property
    def hotwater_button_override_state(self):
        return True if self._data.get("HotWaterButtonOverrideState") == "On" else False

    @property
    def hub_time(self):
        return self._hub_time

    @hub_time.setter
    def hub_time(self, utcTime: int):
        """
        Set the time on the wiser hub to current system time
        return: boolen - true = success, false = failed
        """
        if self._sendCommand({"UnixTime": utcTime}):
            self._hub_time = utcTime

    @property
    def name(self):
        return self._network_data.get(
            "Station", {"MdnsHostname": "WiserHeatxxxxxx"}
        ).get("MdnsHostname")

    @property
    def network(self):
        return _WiserNetwork(self._network_data.get("Station", {}))

    @property
    def opentherm_connection_status(self):
        return self._data.get("OpenThermConnectionStatus", "Disconnected")

    @property
    def pairing_status(self):
        return self._data.get("PairingStatus")

    @property
    def system_mode(self):
        return self._data.get("SystemMode")

    @property
    def timezone_offset(self):
        return self._timezone_offset

    @timezone_offset.setter
    def timezone_offset(self, offset: int):
        if self._sendCommand({"TimeZoneOffset": offset}):
            self._timezone_offset = offset

    @property
    def user_overrides_active(self):
        return self._data.get("UserOverridesActive", False)

    @property
    def valve_protection(self):
        return self._valve_protection_enabled

    @valve_protection.setter
    def valve_protection(self, enabled: bool):
        """
        Set the valve protection setting on the wiser hub
        param enabled: turn on or off
        """
        if self._sendCommand({"ValveProtectionEnabled": enabled}):
            self._valve_protection_enabled = enabled


class _WiserSmartValve(_WiserDevice):
    """ Class representing a Wiser Smart Valve device """

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
        return rest._send_command(WISERSMARTVALVE.format(self.id), cmd)

    @property
    def battery(self):
        return _WiserBattery(self._data)

    @property
    def device_lock_enabled(self):
        return self._device_lock_enabled

    @device_lock_enabled.setter
    def device_lock_enabled(self, enable: bool):
        """
        Set the device lock setting on the smart valve
        param enabled: turn on or off
        """
        return self._send_command({"DeviceLockEnabled": enable})

    @property
    def current_target_temperature(self):
        return _from_wiser_temp(self._device_type_data.get("SetPoint"))

    @property
    def current_temperature(self):
        return _from_wiser_temp(self._device_type_data.get("MeasuredTemperature"))

    @property
    def identify(self):
        return self._indentify_active

    @identify.setter
    def identify(self, enable: bool = False):
        """
        Set the identify function setting on the room stat
        param enabled: turn on or off
        """
        if self._send_command({"Identify": enable}):
            self._indentify_active = enable

    @property
    def mounting_orientation(self):
        return self._device_type_data.get("MountingOrientation")

    @property
    def percentage_demand(self):
        return self._device_type_data.get("PercentageDemand")


class _WiserRoomStat(_WiserDevice):
    """ Class representing a Wiser Room Stat device """

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
        return rest._send_command(WISERROOMSTAT.format(self.id), cmd)

    @property
    def battery(self):
        return _WiserBattery(self._data)

    @property
    def current_humidity(self):
        return self._device_type_data.get("MeasuredHumidity")

    @property
    def current_target_temperature(self):
        return _from_wiser_temp(self._device_type_data.get("SetPoint"))

    @property
    def current_temperature(self):
        return _from_wiser_temp(self._device_type_data.get("MeasuredTemperature"))

    @property
    def device_lock_enabled(self):
        return self._device_lock_enabled

    @device_lock_enabled.setter
    def device_lock_enabled(self, enable: bool):
        """
        Set the device lock setting on the room stat
        param enabled: turn on or off
        """
        return self._send_command({"DeviceLockEnabled": enable})

    @property
    def identify(self):
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
    """ Class representing a Wiser Smart Plug device """

    def __init__(self, data: dict, device_type_data: dict, schedule: _WiserSchedule):
        super().__init__(data)
        self._data = data
        self._device_type_data = device_type_data
        self._schedule = schedule

        self._away_action = device_type_data.get("AwayAction", "Unknown")
        self._mode = device_type_data.get("Mode", "Unknown")
        self._name = device_type_data.get("Name", "Unknown")
        self._output_state = device_type_data.get("OutputState", "Off")

    def _send_command(self, cmd: dict):
        """
        Send control command to the smart plug
        param cmd: json command structure
        return: boolen - true = success, false = failed
        """
        rest = _WiserRestController()
        return rest._send_command(WISERSMARTPLUG.format(self.id), cmd)

    @property
    def away_action(self):
        """
        Current action of the smart plug when away mode is set
        return: str
        """
        return self._away_action

    @away_action.setter
    def away_action(self, action: WiserAwayActionEnum):
        result = self._send_command({"AwayAction": action.value})
        if result:
            self._away_action = action.value

    @property
    def control_source(self):
        """
        Current control source of the smart plug
        return: str
        """
        return self._device_type_data.get("ControlSource", "Unknown")

    @property
    def manual_state(self):
        """
        Current manual mode setting of the smart plug
        return: str
        """
        return self._device_type_data.get("ManualState", "Unknown")

    @property
    def mode(self):
        """
        Current mode of the smart plug
        return: str
        """
        return self._mode

    @mode.setter
    def mode(self, mode: WiserModeEnum):
        if mode == WiserModeEnum.off:
            raise ValueError("You cannot set a smart plug to off mode.")
        else:
            if self._send_command({"Mode": mode.value}):
                self._mode = mode

    @property
    def name(self):
        """
        Name of the msmart plug
        return: str
        """
        return self._name

    @name.setter
    def name(self, name: str):
        if self._send_command({"Name": name}):
            self._name = name

    @property
    def is_on(self):
        """
        Is the smart plug on
        return: boolean
        """
        return True if self._output_state == "On" else False

    @property
    def schedule(self):
        return self._schedule

    @property
    def scheduled_state(self):
        """
        Current scheduled state of the smart plug
        return: str
        """
        return self._device_type_data.get("ScheduledState", "Unknown")

    def turn_on(self):
        """
        Turn on the smart plug
        return: boolean
        """
        result = self._send_command({"RequestOutput": "On"})
        if result:
            self._output_is_on = True
        return result

    def turn_off(self):
        """
        Turn off the smart plug
        return: boolean
        """
        result = self._send_command({"RequestOutput": "Off"})
        if result:
            self._output_is_on = False
        return result


class _WiserRoom(object):
    """ Class representing a Wiser Room entity """

    def __init__(self, data: dict, schedule: _WiserSchedule, devices: _WiserDevice):

        self._data = data
        self._schedule = schedule
        self._devices = devices

        self._mode = data.get("Mode")
        self._name = data.get("Name")
        self._window_detection_active = data.get("WindowDetectionActive", "Unknown")

    def _send_command(self, cmd: dict):
        """
        Send control command to the room
        param cmd: json command structure
        return: boolen - true = success, false = failed
        """
        rest = _WiserRestController()
        return rest._send_command(WISERROOM.format(self.id), cmd)

    @property
    def boost_end_time(self):
        return datetime.datetime.fromtimestamp(
            self._data.get("OverrideTimeoutUnixTime", 0)
        )

    @property
    def boost_time_remaining(self):
        if self._data.get("OverrideTimeoutUnixTime", 0) > 0:
            now = datetime.now()
            boost_end_time = datetime.datetime.fromtimestamp(
                self._data.get("OverrideTimeoutUnixTime", 0)
            )
            return boost_end_time - now
        else:
            return 0

    @property
    def current_target_temperature(self):
        return _from_wiser_temp(self._data.get("CurrentSetPoint", TEMP_MINIMUM))

    @property
    def current_temperature(self):
        return _from_wiser_temp(self._data.get("CalculatedTemperature", TEMP_MINIMUM))

    @property
    def devices(self):
        return self._devices

    @property
    def id(self):
        return self._data.get("id")

    @property
    def is_boosted(self):
        return (
            True
            if self._data.get("SetpointOrigin", "Unknown") == "FromBoost"
            else False
        )

    @property
    def is_heating(self):
        return True if self._data.get("ControlOutputState", "Off") == "On" else False

    @property
    def manual_target_temperature(self):
        return _from_wiser_temp(self._data.get("ManualSetPoint", TEMP_MINIMUM))

    @property
    def mode(self):
        return self._mode

    @mode.setter
    def mode(self, mode: WiserModeEnum):
        if mode == WiserModeEnum.off:
            if self._send_command({"Mode": WiserModeEnum.manual.value}):
                self.current_target_temperature = TEMP_OFF
        elif mode == WiserModeEnum.manual:
            if self._send_command({"Mode": mode.value}):
                if self.current_target_temperature == TEMP_OFF:
                    self._mode = mode.value
                    self.set_manual_temperature(self.manual_target_temperature)
        else:
            if self._send_command({"Mode": mode.value}):
                self._mode = mode.value

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name: str):
        if self._send_command({"Name": name.title()}):
            self._name = name.title()

    @property
    def override_target_temperature(self):
        return self._data.get("OverrideSetpoint", 0)

    @property
    def override_type(self):
        return self._data.get("OverrideType", "None")

    @property
    def percentage_demand(self):
        return self._data.get("PercentageDemand", 0)

    @property
    def schedule(self):
        return self._schedule

    @property
    def schedule_id(self):
        return self._data.get("ScheduleId")

    @property
    def scheduled_target_temperature(self):
        return _from_wiser_temp(self._data.get("ScheduledSetPoint", TEMP_MINIMUM))

    @property
    def target_temperature_origin(self):
        return self._data.get("SetpointOrigin", "Unknown")

    @property
    def window_detection_active(self):
        return self._window_detection_active

    @window_detection_active.setter
    def window_detection_active(self, enabled: bool):
        if self._send_command({"WindowDetectionActive": enabled}):
            self._window_detection_active = enabled

    @property
    def window_state(self):
        return self._data.get("WindowState", "Unknown")

    def set_boost(self, inc_temp: float, duration: int):
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

    def cancel_boost(self):
        """
        Cancel the temperature boost of the room
        return: boolean
        """
        if self.is_boosted:
            return self.cancel_override()
        else:
            return False

    def override_temperature(self, temp: float):
        """
        Set the temperature of the room to override current schedule temp or in manual mode
        param temp: the temperature to set in C
        return: boolean
        """
        return self._send_command(
            {
                "RequestOverride": {
                    "Type": "Manual",
                    "SetPoint": _to_wiser_temp(_validate_temperature(temp)),
                }
            }
        )

    def override_temperature_for_duration(self, temp: float, duration: int):
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
                    "SetPoint": _to_wiser_temp(_validate_temperature(temp)),
                }
            }
        )

    def set_manual_temperature(self, temp: float):
        self.mode = WiserModeEnum.manual
        return self.override_temperature(temp)

    def schedule_advance(self):
        """
        Advance room schedule to the next scheduled time and temperature setting
        return: boolean
        """
        return self.override_temperature(
            _from_wiser_temp(self.schedule.next.get("DegreesC"))
        )

    def cancel_override(self):
        """
        Set room schedule to the current scheduled time and temperature setting
        return: boolean
        """
        return self._send_command({"RequestOverride": {"Type": "None"}})


class _WiserHeating:
    """ Class representing a Wiser Heating Channel """

    def __init__(self, data: dict, rooms: dict):
        self._data = data
        self._rooms = rooms

    @property
    def demand_on_off_output(self):
        return self._data.get("DemandOnOffOutput", "Unknown")

    @property
    def heating_relay_status(self):
        return self._data.get("HeatingRelayState", "Unknown")

    @property
    def id(self):
        return self._data.get("id")

    @property
    def is_smart_valve_preventing_demand(self):
        return self._data.get(
            "IsSmartValvePreventingDemand", False
        )

    @property
    def name(self):
        return self._data.get("Name", "Unknown")

    @property
    def percentage_demand(self):
        return self._data.get("PercentageDemand", 0)

    @property
    def rooms(self):
        rooms = []
        for room in self._rooms:
            if room.id in self.room_ids:
                rooms.append(room)
        return rooms

    @property
    def room_ids(self):
        return self._data.get("RoomIds", [])

    


class _WiserHotwater:
    """ Class representing a Wiser Hot Water controller """

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
        return rest._send_command(WISERHOTWATER.format(self.id), cmd)

    @property
    def current_control_source(self):
        return self._data.get("HotWaterDescription", "Unknown")

    @property
    def id(self):
        return self._data.get("id")

    @property
    def is_heating(self):
        return True if self._data.get("WaterHeatingState") == "On" else False

    @property
    def is_boosted(self):
        return True if self._data.get("Override") else False  # TODO: Check this

    @property
    def mode(self):
        return self._mode

    @mode.setter
    def mode(self, mode: WiserModeEnum):
        if mode == WiserModeEnum.off:
            if self._send_command({"Mode": WiserModeEnum.manual.value}):
                self.set_override_off()
        else:
            if self._send_command({"Mode": mode.value}):
                self._mode = mode.value

    @property
    def schedule(self):
        return self._schedule

    def set_override_on(self):
        """
        Turn on hotwater.  In auto this is until next schedule event.  In manual modethis is on until changed.
        return: boolean
        """
        return self._send_command(
            {"RequestOverride": {"Type": "Manual", "SetPoint": _to_wiser_temp(HW_ON)}}
        )

    def set_override_on_for_duration(self, duration: int):
        """
        Boost the hot water for x minutes
        param temp: the boost temperature to set in C
        param duration: the duration to boost the room temperature in minutes
        return: boolean
        """
        return self._send_command(
            {
                "RequestOverride": {
                    "Type": "Manual",
                    "DurationMinutes": duration,
                    "SetPoint": _to_wiser_temp(HW_ON),
                    "Originator": "App",
                }
            }
        )

    def set_override_off(self):
        """
        Turn off hotwater.  In auto this is until next schedule event.  In manual modethis is on until changed.
        return: boolean
        """
        return self._send_command(
            {"RequestOverride": {"Type": "Manual", "SetPoint": _to_wiser_temp(HW_OFF)}}
        )

    def set_override_off_for_duration(self, duration: int):
        """
        Boost the hot water for x minutes
        param temp: the boost temperature to set in C
        param duration: the duration to boost the room temperature in minutes
        return: boolean
        """
        return self._send_command(
            {
                "RequestOverride": {
                    "Type": "Manual",
                    "DurationMinutes": duration,
                    "SetPoint": _to_wiser_temp(HW_OFF),
                    "Originator": "App",
                }
            }
        )

    def cancel_overrides(self):
        """
        Cancel all overrides of the hot water
        return: boolean
        """
        return self._send_command({"RequestOverride": {"Type": "None"}})


"""
Support Classess
"""


class _WiserNetwork:
    """ Data structure for network information for a Wiser Hub """

    def __init__(self, data: dict):
        self._data = data

        self._dhcp_status = data.get("DhcpStatus", {})
        self._network_interface = data.get("NetworkInterface", {})


    @property
    def dhcp_mode(self):
        return self._data.get("NetworkInterface", {}).get("DhcpMode", "Unknown")

    @property
    def hostname(self):
        return self._data.get("NetworkInterface", {}).get("HostName", "Unknown")

    @property
    def ip_address(self):
        if self.dhcp_mode == "Client":
            return self._dhcp_status.get("IPv4Address", "Unknown")
        else:
            return self._network_interface.get("IPv4HostAddress", "Unknown")

    @property
    def ip_subnet_mask(self):
        if self.dhcp_mode == "Client":
            return self._dhcp_status.get("IPv4SubnetMask", "Unknown")
        else:
            return self._network_interface.get("IPv4SubnetMask", "Unknown")

    @property
    def ip_gateway(self):
        if self.dhcp_mode == "Client":
            return self._dhcp_status.get("IPv4DefaultGateway", "Unknown")
        else:
            return self._network_interface.get("IPv4DefaultGateway", "Unknown")

    @property
    def ip_primary_dns(self):
        if self.dhcp_mode == "Client":
            return self._dhcp_status.get("IPv4PrimaryDNS", "Unknown")
        else:
            return self._network_interface.get("IPv4PrimaryDNS", "Unknown")

    @property
    def ip_secondary_dns(self):
        if self.dhcp_mode == "Client":
            return self._dhcp_status.get("IPv4SecondaryDNS", "Unknown")
        else:
            return self._network_interface.get("IPv4SecondaryDNS", "Unknown")

    @property
    def mac_address(self):
        return self._data.get("MacAddress", "Unknown")

    @property
    def signal_percent(self):
        return min(100, int(2 * (self._data.get("RSSI", {}).get("Current", 0) + 100)))

    @property
    def signal_rssi(self):
        return self._data.get("RSSI", {}).get("Current", 0)

    @property
    def security_mode(self):
        return self._data.get("SecurityMode", "Unknown")

    @property
    def ssid(self):
        return self._data.get("SSID", "Unknown")


class _WiserCloud:
    """ Data structure for cloud information for a Wiser Hub """

    def __init__(self, cloud_status: str, data: dict):
        self._cloud_status = cloud_status
        self._data = data

    @property
    def api_host(self):
        return self._data.get("WiserApiHost")

    @property
    def bootstrap_api_host(self):
        return self._data.get("BootStrapApiHost")

    @property
    def connection_status(self):
        return self._cloud_status

    @property
    def detailed_publishing(self):
        return self._data.get("DetailedPublishing")

    @property
    def diagnostic_telemetry_enabled(self):
        return self._data.get("EnableDiagnosticTelemetry")

    @property
    def environment(self):
        return self._data.get("Environment")
 

class _WiserBattery:
    """ Data structure for battery information for a Wiser device that is powered by batteries """

    def __init__(self, data: dict):
        self._data = data
    
    @property
    def level(self):
        return self._data.get("BatteryLevel", "NoBattery")

    @property
    def percent(self):
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
    def voltage(self):
        return self._data.get("BatteryVoltage", 0) / 10



class _WiserSignal:
    """ Data structure for zigbee signal information for a Wiser device """

    def __init__(self, data: dict):
        self._data = data

    @property
    def displayed_signal_strength(self):
        return self._data.get("DisplayedSignalStrength")

    @property
    def controller_rssi(self):
        return self._data.get("ReceptionOfController", {"Rssi": 0}).get(
            "Rssi"
        )

    @property
    def controller_lqi(self):
        return self._data.get("ReceptionOfController", {"Lqi": 0}).get("Lqi")

    @property
    def controller_signal_percent(self):
        return min(100, int(2 * (self.controller_rssi + 100)))

    @property
    def device_rssi(self):
        return self._data.get("ReceptionOfDevice", {"Rssi": 0}).get("Rssi")

    @property
    def device_lqi(self):
        return self._data.get("ReceptionOfDevice", {"Lqi": 0}).get("Lqi")

    @property
    def device_signal_percent(self):
        return min(100, int(2 * (self.device_rssi + 100)))


class _WiserGPS:
    """ Data structure for gps positional information for a Wiser Hub """

    def __init__(self, data: dict):
        self._data = data

    @property
    def latitude(self):
        return self._data.get("Latitude")

    @property
    def longitude(self):
        return self._data.get("Longitude")


class _WiserScheduleNext:
    """ Data structure for schedule next entry data """

    def __init__(self, schedule_type: str, data: dict):
        self._schedule_type = schedule_type
        self._data = data

    @property
    def day(self):
        return self._data.get("Day", "")

    @property
    def time(self):
        return self._data.get("Time", 0)

    @property
    def setting(self):
        if self._schedule_type == "Heating":
            return self._data.get("DegreesC")
        if self._schedule_type == "OnOff":
            return self._data.get("State")
        return None


def _validate_temperature(temp: float):
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


def _to_wiser_temp(temp: float):
    """
    Converts from temperature to wiser hub format
    param temp: The temperature to convert
    return: Integer
    """
    temp = int(temp * 10)
    return temp


def _from_wiser_temp(temp: int):
    """
    Conerts from wiser hub temperature format to decimal value
    param temp: The wiser temperature to convert
    return: Float
    """
    if temp is not None:
        if temp >= TEMP_ERROR:  # Fix high value from hub when lost sight of iTRV
            temp = TEMP_MINIMUM
        else:
            temp = round(temp / 10, 1)
    return temp