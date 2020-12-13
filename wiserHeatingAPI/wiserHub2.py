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
TEMP_MINIMUM = 5
TEMP_MAXIMUM = 30
TEMP_OFF = -20

# Battery Constants
ROOMSTAT_MIN_BATTERY_LEVEL = 1.7
ROOMSTAT_FULL_BATTERY_LEVEL = 2.7
TRV_FULL_BATTERY_LEVEL = 3.0
TRV_MIN_BATTERY_LEVEL = 2.5

# Other Constants
MDNS_TIMEOUT = 10
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
WEEKDAYS = ["Monday","Tuesday","Wednesday","Thursday","Friday"]
WEEKENDS = ["Saturday","Sunday"]
SPECIAL_DAYS = [TEXT_WEEKDAYS,TEXT_WEEKENDS]

# Wiser Hub Rest Api URL Constants
WISERHUBURL         = "http://{}/data/v2/"
WISERHUBDOMAIN      = WISERHUBURL + "domain/"
WISERHUBNETWORK     = WISERHUBURL + "network/"
WISERHUBSCHEDULES   = WISERHUBURL + "schedules/"
WISERSYSTEM         = "System"
WISERHOTWATER       = "HotWater/{}"
WISERROOM           = "Room/{}"
WISERSMARTVALVE     = "SmartValve/{}"
WISERROOMSTAT       = "RoomStat/{}"
WISERSMARTPLUG      = "SmartPlug/{}"


_LOGGER = logging.getLogger(__name__)

# Set traceback limit
sys.tracebacklimit = TRACEBACK_LIMIT

"""
Exception Handlers
"""
class Error(Exception):
    """Base class for exceptions in this module."""
    pass

class WiserNoDevicesFound(Error):
    pass

class wiserNotSupported(Error):
    pass

class WiserNotFound(Error):
    pass

class WiserNoHotWaterFound(Error):
    pass

class WiserNoHeatingFound(Error):
    pass

class WiserRESTException(Error):
    pass

class WiserHubDataNull(Error):
    _LOGGER.info("WiserHub data null after refresh")
    pass

class WiserHubAuthenticationException(Error):
    pass

class WiserHubTimeoutException(Error):
    pass

class WiserNoRoomsFound(Error):
    pass

class WiserNotImplemented(Error):
    _LOGGER.info("Function not yet implemented")
    pass

class _wiserConnection:
    def __init(self):
        self.host = None
        self.secret = None
        self.hubName = None

_wiserApiConnection = _wiserConnection()

class wiserAPI():
    """ Main api class to access all entities and attributes of wiser system """
    def __init__(self, host: str, secret: str):
        self.host = host
        self.secret = secret
        #self.hubName = ""
        
        # Main data stores
        self.domainData = {}
        self.networkData = {}
        self.scheduleData = {}

        # Hub entities
        self.schedules = []
        self.hub = None
        self.devices = []
        self.smartValves = []
        self.smartPlugs = []
        self.roomStats = []
        self.rooms = []
        self.hotwater = None
        self.heating = None
        
        _LOGGER.info(
            "WiserHub API Initialised : Version {}".format(__VERSION__)
        )

        # Set hub secret to global object
        _wiserApiConnection.secret = self.secret

        # Do hub discovery if null IP is passed when initialised
        if self.host is None:
            wiserDiscover = wiserDiscovery()
            hub = wiserDiscover.discoverHub()
            if len(hub) > 0:
                _wiserApiConnection.hubName = hub[0]["name"]
                _wiserApiConnection.host = hub[0]["hostname"]

                print("Hub: {}, IP: {}".format(_wiserApiConnection.hubName, _wiserApiConnection.host))
            else:
                print("No Wiser hub discovered on network")
        else:
            _wiserApiConnection.host = self.host

        # Read hub data if hub IP and secret exist
        if _wiserApiConnection.host is not None and _wiserApiConnection.secret is not None:
            self.readHubData()  
            #TODO - Add validation function to check for no devices, rooms etc here.      
        else:
            print("No connection info")

    def readHubData(self):
        """ Read all data from hub and populate objects """
        # Read hub data endpoints
        hubData = _wiserRestController()
        self.domainData = hubData._getHubData(WISERHUBDOMAIN)
        self.networkData = hubData._getHubData(WISERHUBNETWORK)
        self.scheduleData = hubData._getHubData(WISERHUBSCHEDULES)
        
        # Schedules
        self.schedules = []
        for scheduleType in self.scheduleData:
            for schedule in self.scheduleData.get(scheduleType):
                self.schedules.append(
                    _wiserSchedule(scheduleType, schedule)
                )

        # Devices
        self.devices = []
        self.hub = None
        self.smartValves = []
        self.roomStats = []
        self.smartPlugs = []
        if self.domainData.get("Device"):
            for device in self.domainData.get("Device"):
                # Add to generic device list
                self.devices.append(_wiserDevice(device))

                # Add device to specific device type
                if (device.get("ProductType") == "Controller"):
                    self.hub = _wiserHub(
                        self.domainData.get("System"),
                        device,
                        self.networkData,
                        self.domainData.get("Cloud")
                    )
                if (device.get("ProductType") == "iTRV"):
                    # Get smartValve info
                    smartValveInfo = [smartValve for smartValve in self.domainData.get("SmartValve") if smartValve.get("id") == device.get("id")]
                    # Add entity
                    self.smartValves.append(
                        _wiserSmartValve(
                            device,
                            smartValveInfo[0]
                        )
                    )
                elif (device.get("ProductType") == "RoomStat"):
                    # Get roomStat info
                    roomStatInfo = [roomStat for roomStat in self.domainData.get("RoomStat") if roomStat.get("id") == device.get("id")]
                    # Add entity
                    self.roomStats.append(
                        _wiserRoomStat(
                            device,
                            roomStatInfo[0]
                        )
                    )
                elif (device.get("ProductType") == "SmartPlug"):
                    # Get smartPlug info
                    smartPlugInfo = [smartPlug for smartPlug in self.domainData.get("SmartPlug") if smartPlug.get("id") == device.get("id")]
                    #Get schedule
                    smartPlugSchedule = [schedule for schedule in self.schedules if schedule.id == smartPlugInfo[0].get("ScheduleId")]
                    #Add entity
                    self.smartPlugs.append(
                        _wiserSmartPlug(
                            device,
                            smartPlugInfo[0],
                            smartPlugSchedule[0]
                        )
                    )

        # Rooms
        if self.domainData.get("Room"):
            self.rooms = [
                _wiserRoom(
                    room, 
                    self.getScheduleById(room.get("ScheduleId")),
                    [device for device in self.devices if (device.id in room.get("SmartValveIds",["0"]) or device.id == room.get("RoomStatId","0"))]
                ) for room in self.domainData.get("Room")
            ]

        # Hot Water
        if self.domainData.get("HotWater"):
            self.hotwater = _wiserHotwater(
                self.domainData.get("HotWater",{})[0],
                self.getScheduleById(self.domainData.get("HotWater",{})[0].get("ScheduleId",0)),
            )

        # Heating
        if self.domainData.get("HeatingChannel"):
            self.heating = _wiserHeating(
                self.domainData.get("HeatingChannel",[])
            )

    """
    Find entities by id or name
    """
    # Rooms   
    def getRoomById(self, id: int):
        """
        Gets a room object from the rooms id
        param id: id of room
        return: _wiserRoom object
        """
        try:
            return [room for room in self.rooms if room.id == id][0]
        except IndexError:
            return None

    def getRoomByName(self, name: str):
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
    def getScheduleById(self, id: int):
        """
        Gets a schedule object from the schedules id
        param id: id of schedule
        return: _wiserSchedule object
        """
        try:
            return [schedule for schedule in self.schedules if schedule.id == id][0]
        except IndexError:
            return None

    # Devices
    def getDeviceById(self, id: int):
        """
        Gets a device object from the devices id
        param id: id of device
        return: _wiserDevice object
        """
        try:
            return [device for device in self.devices if device.id == id][0]
        except IndexError:
            return None

    def getDeviceByNodeId(self, nodeId: int):
        """
        Gets a device object from the devices zigbee node id
        param nodeId: zigbee node id of device
        return: _wiserDevice object
        """
        try:
            return [device for device in self.devices if device.nodeId == nodeId][0]
        except IndexError:
            return None

    # Smartvalves
    def getSmartValveById(self, id: int):
        """
        Gets a SmartValve object from the SmartValves id
        param id: id of smart valve
        return: _wiserSmartValve object
        """
        try:
            return [smartValve for smartValve in self.smartValves if smartValve.id == id][0]
        except IndexError:
            return None

    # Smartplugs
    def getSmartPlugById(self, id: int):
        """
        Gets a SmartPlug object from the SmartPlugs id
        param id: id of smart plug
        return: _wiserSmartPlug object
        """
        try:
            return [smartPlug for smartPlug in self.smartPlugs if smartPlug.id == id][0]
        except IndexError:
            return None

    # Roomstats
    def getRoomStatById(self, id: int):
        """
        Gets a RoomStat object from the RoomStatss id
        param id: id of room stat
        return: _wiserRoomStat object
        """
        try:
            return [roomStat for roomStat in self.roomStats if roomStat.id == id][0]
        except IndexError:
            return None


class _wiserRestController:
    """ Class to handle getting data from and sending commands to a wiser hub """
    def _getHeaders(self):
        """
        Define headers for wiser hub api calls 
        return: json object
        """
        return {
            "SECRET": _wiserApiConnection.secret,
            "Content-Type": "application/json;charset=UTF-8",
        }

    def _getHubData(self, url: str):
        """
        Read data from hub and raise errors if fails
        param url: url of hub rest api endpoint
        return: json object
        """
        url = url.format(_wiserApiConnection.host)
        try:
            resp = requests.get(
                url,
                headers=self._getHeaders(),
                timeout=REST_TIMEOUT,
            )
            resp.raise_for_status()

        #TODO - Tidy this up!!!
        except requests.Timeout:
            _LOGGER.debug(
                "Connection timed out trying to update from Wiser Hub"
            )
            raise WiserHubTimeoutException("The connection timed out.")

        except requests.HTTPError as ex:
            if ex.response.status_code == 401:
                raise WiserHubAuthenticationException(
                    "Authentication error.  Check secret key."
                )
            elif ex.response.status_code == 404:
                raise WiserRESTException("Not Found.")
            else:
                raise WiserRESTException("Unknown Error.")

        except requests.ConnectionError:
            _LOGGER.debug("Connection error trying to update from Wiser Hub")
            raise
        
        return resp.json()

    def _sendCommand(self, url: str, commandData: dict):
        """
        Send control command to hub and raise errors if fails
        param url: url of hub rest api endpoint
        param patchData: json object containing command and values to set
        return: boolean
        """
        url = WISERHUBDOMAIN.format(_wiserApiConnection.host) + url
        return self._patchData(url, commandData)

    def _sendSchedule(self, url: str, scheduleData: dict):
        """
        Send schedule to hub and raise errors if fails
        param url: url of hub rest api endpoint
        param patchData: json object containing command and values to set
        return: boolean
        """
        url = url.format(_wiserApiConnection.host)
        return self._patchData(url, scheduleData)

    def _patchData(self, url: str, patchData: dict):
        """
        Send patch update to hub and raise errors if fails
        param url: url of hub rest api endpoint
        param patchData: json object containing command and values to set
        return: boolean
        """
        _LOGGER.debug("patchdata {} ".format(patchData))
        response = requests.patch(
            url=url,
            headers=self._getHeaders(),
            json=patchData,
            timeout=REST_TIMEOUT,
        )
        #print("Request: ", response.request.body)
        if response.status_code != 200:
            _LOGGER.debug(
                "Set {} Response code = {}".format(
                    patchData, response.status_code
                )
            )
            raise WiserRESTException(
                "Error setting {} , error {} {}".format(
                    patchData, response.status_code, response.text
                )
            )
        else:
            return True


class wiserDiscovery:
    """ Class to handle mDns discovery of a wiser hub on local network """
    def __init__(self):
        self.discoveredHubs = []

    def _zeroconf_on_service_state_change(
        self, zeroconf: Zeroconf, service_type: str, name: str, state_change: ServiceStateChange
    ) -> None:
        """
        Look for Wiser Hub in discovered services and set IP and Name in global vars
        """
        if state_change is ServiceStateChange.Added:
            if "WiserHeat" in name:
                _LOGGER.info("Discovered Hub")
                info = zeroconf.get_service_info(service_type, name)
                if info:
                    addresses = ["%s:%d" % (addr, cast(int, info.port)) for addr in info.parsed_addresses()]
                    hub = {
                        "ip": addresses[0].replace(":80",""),
                        "name": info.server.replace(".local.",""),
                        "hostname": info.server.replace(".local.",".local").lower()
                    }
                    self.discoveredHubs.append(hub)

    def discoverHub(self):
        """
        Call zeroconf service browser until hub found or timeout
        return: boolean - true = hub found, false = hub not found
        """
        timeout = 0

        zeroconf = Zeroconf()
        services = ["_http._tcp.local."]
        ServiceBrowser(zeroconf, services, handlers=[self._zeroconf_on_service_state_change])

        while len(self.discoveredHubs) < 1 and timeout < MDNS_TIMEOUT * 10:
            sleep(0.1)
            timeout += 1

        zeroconf.close()
        return self.discoveredHubs


class _wiserDevice:
    """ Class representing a wiser device """
    def __init__(self, data: dict):
        self.id = data.get("id")
        self.nodeId = data.get("NodeId",0)
        self.productType = data.get("ProductType","Unknown")
        self.modelIdentifier = data.get("ModelIdentifier","Unknown")
        self.firmwareVersion = data.get("ActiveFirmwareVersion","Unknown")
        self.serialNo = data.get("SerialNumber","Unknown")
        self.parentNodeId = data.get("ParentNodeId",0)
        self.signal = _wiserSignal(data)


class _wiserSchedule:
    """
    Class representing a wiser Schedule
    """
    def __init__(self, scheduleType: str, scheduleData: dict):
        self.type = scheduleType
        self.id = scheduleData.get("id")
        self.name = scheduleData.get("Name")
        self.next = scheduleData.get("Next")
        self.currentTargetTemperature = _fromWiserTemp(scheduleData.get("CurrentSetpoint"))
        self.currentState = scheduleData.get("CurrentState", "Unknown")
        self.scheduleData = self._remove_schedule_elements(scheduleData)

    def _remove_schedule_elements(self, scheduleData: dict):
        removeList = ["id","CurrentSetpoint","CurrentState","Name","Next"]
        for item in removeList:
            if item in scheduleData:
                del scheduleData[item]
        return scheduleData

    def _convert_from_wiser_schedule(self, scheduleData: dict):
        """
        Convert from wiser format to format suitable for yaml output
        param: scheduleData
        param: mode
        """
        # Create dict to take converted data
        schedule_output = {
            "Name": self.name,
            "Description": self.type + " schedule for " + self.name,
            "Type": self.type,
        }
        # Iterate through each day
        try:
            for day, sched in scheduleData.items():
                if day.title() in (WEEKDAYS + WEEKENDS + SPECIAL_DAYS):
                    schedule_set_points = self._convert_wiser_to_yaml_day(sched, self.type)
                    schedule_output.update({day.capitalize(): schedule_set_points})
            return schedule_output
        except:
            return None

    def _convert_to_wiser_schedule(self, scheduleYamlData: dict):
        """
        Convert from wiser format to format suitable for yaml output
        param: scheduleData
        param: mode
        """
        schedule_output = {}
        try:
            for day, sched in scheduleYamlData.items():
                if day.title() in (WEEKDAYS + WEEKENDS + SPECIAL_DAYS):
                    schedule_day = self._convert_yaml_to_wiser_day(sched, self.type)
                    # If using special days, convert to one entry for each day of week
                    if day.title() in SPECIAL_DAYS:
                        if day.title() == TEXT_WEEKDAYS:
                            for weekday in WEEKDAYS:
                                schedule_output.update({weekday: schedule_day})
                        if day.lower() == TEXT_WEEKENDS:
                            for weekend_day in WEEKENDS:
                                schedule_output.update({weekend_day: schedule_day})
                    else:
                        schedule_output.update({day: schedule_day})
            return schedule_output
        except:
            return None

    def _convert_wiser_to_yaml_day(self, daySchedule, scheduleType):
        """
        Convert from wiser schedule format to format for yaml output.
        param daySchedule: json schedule for a day in wiser v2 format
        param scheduleType: Heating or OnOff
        return: json
        """
        schedule_set_points = []
        if scheduleType == TEXT_HEATING:
            for i in range(len(daySchedule[TEXT_TIME])):
                schedule_set_points.append({
                    TEXT_TIME:
                    (datetime.strptime(format(daySchedule[TEXT_TIME][i], "04d"), "%H%M")).strftime("%H:%M"),
                    TEXT_TEMP:
                    _fromWiserTemp(daySchedule[TEXT_DEGREESC][i])
                })
        else:
            for i in range(len(daySchedule)):
                schedule_set_points.append({
                    TEXT_TIME:
                    (datetime.strptime(format(abs(daySchedule[i]), "04d"), "%H%M")).strftime("%H:%M"),
                    TEXT_STATE:
                    TEXT_ON if daySchedule[i] > 0 else TEXT_OFF
                })
        return schedule_set_points

    def _convert_yaml_to_wiser_day(self, daySchedule, scheduleType):
        """
        Convert from yaml format to wiser v2 schedule format.
        param daySchedule: json schedule for a day in yaml format
        param scheduleType: Heating or OnOff
        return: json
        """
        times = []
        temps = []
        
        if scheduleType == TEXT_HEATING:
            for item in daySchedule:
                for key, value in item.items():
                    if key.title() == TEXT_TIME:
                        time = str(value).replace(":", "")
                        times.append(time)
                    if key.title() == TEXT_TEMP:
                        temp = _toWiserTemp(_validateTemperature(value if str(value).title() != TEXT_OFF else TEMP_OFF))
                        temps.append(temp)
            return {
                TEXT_TIME: times,
                TEXT_DEGREESC: temps
            }
        else:
            for time, state in daySchedule:
                try:
                    time = int(str(time).replace(":", ""))
                    if state.title() == TEXT_OFF:
                        time = 0 - int(time)
                except:
                    time = 0
                times.append(time)
            return times

    def _sendSchedule(self, scheduleData: dict, id: int = 0) -> bool:
        """
        Send system control command to Wiser Hub
        param cmd: json command structure
        return: boolen - true = success, false = failed
        """
        if id == 0: id = self.id
        rest = _wiserRestController()
        return rest._sendSchedule(WISERHUBSCHEDULES + "/{}/{}".format(self.type, id), scheduleData)

    def saveScheduleToFile(self, scheduleFile: str):
        """
        Save this schedule to a file as json.
        param scheduleFile: file to write schedule to
        return: boolen - true = successfully saved, false = failed to save
        """
        try:
            with open(scheduleFile, 'w') as file:
                json.dump(self.scheduleData, file)
            return True
        except:
            return False

    def saveScheduleToFileYaml(self, scheduleFile: str):
        """
        Save this schedule to a file as yaml.
        param scheduleFile: file to write schedule to
        return: boolen - true = successfully saved, false = failed to save
        """
        try:
            yaml = YAML()
            with open(scheduleFile, 'w') as file:
                yaml.dump(self._convert_from_wiser_schedule(self.scheduleData), file)
            return True
        except:
            return False

    def setSchedule(self, scheduleData: dict):
        """
        Set new schedule
        param scheduleData: json data respresenting a schedule
        return: boolen - true = successfully set, false = failed to set
        """
        return self._sendSchedule(scheduleData)

    def setScheduleFromFile(self, scheduleFile: str):
        """
        Set schedule from file.
        param scheduleFile: file of json data respresenting a schedule
        return: boolen - true = successfully set, false = failed to set
        """
        try:
            with open(scheduleFile, 'r') as file:
                self.setSchedule(json.load(file))
                return True
        except:
            return False

    def setScheduleFromYamlFile(self, scheduleFile: str):
        """
        Set schedule from file.
        param scheduleFile: file of yaml data respresenting a schedule
        return: boolen - true = successfully set, false = failed to set
        """
        try:
            yaml = YAML(typ='safe', pure=True)
            with open(scheduleFile, 'r') as file:
                y = yaml.load(file)
                self.setSchedule(self._convert_to_wiser_schedule(y))
                return True
        except:
            return False

    def copySchedule(self, toId: int):
        """
        Copy this schedule to another schedule
        param toId: id of schedule to copy to
        return: boolen - true = successfully set, false = failed to set
        """
        return self._sendSchedule(self.scheduleData, toId)


class _wiserHub:
    """ Class representing a Wiser Hub device """
    def __init__(self, data: dict, deviceData: dict, networkData: dict, cloudData: dict):
        self.activeFirmware = data.get("ActiveSystemVersion")
        self.automaticDaylightSaving = data.get("AutomaticDaylightSaving")
        self.awayModeAffectsHotWater = data.get("AwayModeAffectsHotWater", False)
        self.awayModeTargetTemperature = _fromWiserTemp(data.get("AwayModeSetPointLimit", 0))
        self.boilerFuelType = data.get("BoilerSettings", {"FuelType":"Unknown"}).get("FuelType")
        self.brandName = data.get("BrandName")
        self.cloud = _wiserCloud(data.get("CloudConnectionStatus"), cloudData)
        self.comfortModeEnabled = data.get("ComfortModeEnabled", False)
        self.degradedModeTargetTemperature = data.get("DegradedModeSetpointThreshold",0)
        self.ecoModeEnabled = data.get("EcoModeEnabled", False)
        self.fotaEnabled = data.get("FotaEnabled")  # firmware over the air
        self.geoPosition = _wiserGPS(data.get("GeoPosition", {}))
        self.heatingButtonOverrideState = data.get("HeatingButtonOverrideState")
        self.hotWaterButtonOverrideState = data.get("HotWaterButtonOverrideState")
        self.hubTime = data.get("LocalDateAndTime")
        self.network = _wiserNetwork(networkData.get("Station", {}))
        self.openThermConnectionStatus = data.get("OpenThermConnectionStatus", "Disconnected")
        self.pairingStatus = data.get("PairingStatus")
        self.systemMode = data.get("SystemMode")
        self.timezoneOffset = data.get("TimeZoneOffset")
        self.userOverridesActive = data.get("UserOverridesActive", False)
        self.valveProtectionEnabled = data.get("ValveProtectionEnabled", False)

    def _sendCommand(self, cmd: dict) -> bool:
        """
        Send system control command to Wiser Hub
        param cmd: json command structure
        return: boolen - true = success, false = failed
        """
        rest = _wiserRestController()
        return rest._sendCommand(WISERSYSTEM, cmd)

    def setTime(self, utcTime: int):
        """
        Set the time on the wiser hub to current system time
        return: boolen - true = success, false = failed
        """
        return self._sendCommand({"UnixTime": utcTime})

    def setValveProtection(self, enabled: bool = False):
        """
        Set the valve protection setting on the wiser hub
        param enabled: turn on or off
        return: boolean
        """
        return self._sendCommand({"ValveProtectionEnabled": enabled})

    def setEcoMode(self, enabled: bool = False):
        """
        Set the eco mode setting on the wiser hub
        param enabled: turn on or off
        return: boolean
        """
        return self._sendCommand({"EcoModeEnabled": enabled})

    def setComfortMode(self, enabled: bool = False):
        """
        Set the comfort setting on the wiser hub
        param enabled: turn on or off
        return: boolean
        """
        return self._sendCommand({"ComfortModeEnabled": enabled})

    def setAwayModeAffectsHotWater(self, enabled: bool = False):
        """
        Set the away mode affects hot water setting on the wiser hub
        param enabled: turn on or off
        return: boolean
        """
        return self._sendCommand({"AwayModeAffectsHotWater": str(enabled).lower()})

    def setAwayModeTargetTemperature(self, temp: float = DEFAULT_AWAY_MODE_TEMP):
        """
        Set the away mode target temperature on the wiser hub
        param temp: the temperature in C
        return: boolean
        """
        return self._sendCommand({"AwayModeSetPointLimit": _toWiserTemp(_validateTemperature(temp))})

    def setDegradedModeTargetTemperature(self, temp: float = DEFAULT_DEGRADED_TEMP):
        """
        Set the degraded mode target temperature on the wiser hub
        param temp: the temperature in C
        return: boolean
        """
        return self._sendCommand({"DegradedModeSetpointThreshold": _toWiserTemp(_validateTemperature(temp))})

    def setAwayMode(self, enabled: bool = False):
        """
        Set the away mode setting on the wiser hub
        param enabled: turn on or off
        return: boolean
        """
        return self._sendCommand({"RequestOverride":{"Type": 2 if enabled else 0}})


class _wiserSmartValve(_wiserDevice):
    """ Class representing a Wiser Smart Valve device """
    def __init__(self, data: dict, deviceTypeData: dict):
        super().__init__(data)
        self.battery = _wiserBattery(data)
        self.currentTargetTemperature = _fromWiserTemp(deviceTypeData.get("SetPoint"))
        self.currentTemperature = _fromWiserTemp(deviceTypeData.get("MeasuredTemperature"))
        self.deviceLockEnabled = data.get("DeviceLockEnabled", False)
        self.mountingOrientation = deviceTypeData.get("MountingOrientation")
        self.percentageDemand = deviceTypeData.get("PercentageDemand")
        self.windowState = deviceTypeData.get("WindowState")

    def _sendCommand(self, cmd: dict):
        """
        Send control command to the smart valve
        param cmd: json command structure
        return: boolen - true = success, false = failed
        """
        rest = _wiserRestController()
        return rest._sendCommand(WISERSMARTVALVE.format(self.id), cmd)

    def identify(self, enable: bool = False):
        """
        Set the identify function setting on the smart valve
        param enabled: turn on or off
        return: boolean
        """
        return self._sendCommand({"Identify": enable})

    def deviceLock(self, enable: bool = False):
        """
        Set the device lock setting on the smart valve
        param enabled: turn on or off
        return: boolean
        """
        return self._sendCommand({"DeviceLockEnabled": enable})


class _wiserRoomStat(_wiserDevice):
    """ Class representing a Wiser Room Stat device """
    def __init__(self, data, deviceTypeData):
        super().__init__(data)
        self.battery = _wiserBattery(data)
        self.currentHumidity = deviceTypeData.get("MeasuredHumidity")
        self.currentTargetTemperature = _fromWiserTemp(deviceTypeData.get("SetPoint"))
        self.currentTemperature = _fromWiserTemp(deviceTypeData.get("MeasuredTemperature"))
        self.deviceLockEnabled = data.get("DeviceLockEnabled", False)

    def _sendCommand(self, cmd: dict):
        """
        Send control command to the room stat
        param cmd: json command structure
        return: boolen - true = success, false = failed
        """
        rest = _wiserRestController()
        return rest._sendCommand(WISERROOMSTAT.format(self.id), cmd)

    def identify(self, enable: bool = False):
        """
        Set the identify function setting on the room stat
        param enabled: turn on or off
        return: boolean
        """
        return self._sendCommand({"Identify": enable})

    def deviceLock(self, enable: bool = False):
        """
        Set the device lock setting on the room stat
        param enabled: turn on or off
        return: boolean
        """
        return self._sendCommand({"DeviceLockEnabled": enable})


class _wiserSmartPlug(_wiserDevice):
    """ Class representing a Wiser Smart Plug device """
    def __init__(self, data: dict, deviceTypeData: dict, schedule: _wiserSchedule):
        super().__init__(data)
        self.awayAction = deviceTypeData.get("AwayAction", "Unknown")
        self.controlSource = deviceTypeData.get("ControlSource", "Unknown")
        self.currentState = deviceTypeData.get("OutputState", "Unknown")
        self.manualState = deviceTypeData.get("ManualState", "Unknown")
        self.mode = deviceTypeData.get("Mode", "Unknown")
        self.name = deviceTypeData.get("Name", "Unknown")
        self.schedule = schedule
        self.scheduledState = deviceTypeData.get("ScheduledState", "Unknown")

    def _sendCommand(self, cmd: dict):
        """
        Send control command to the smart plug
        param cmd: json command structure
        return: boolen - true = success, false = failed
        """
        rest = _wiserRestController()
        return rest._sendCommand(WISERSMARTPLUG.format(self.id), cmd)

    def setModeAuto(self):
        """
        Set the mode to auto setting on the smart plug
        return: boolean
        """
        return self._sendCommand({"Mode": "Auto"})

    def setModeManual(self):
        """
        Set the mode to manual setting on the smart plug
        return: boolean
        """
        return self._sendCommand({"Mode": "Manual"})

    def turnOn(self):
        """
        Turn on the smart plug
        return: boolean
        """
        return self._sendCommand({"RequestOutput": "On"})

    def turnOff(self):
        """
        Turn off the smart plug
        return: boolean
        """
        return self._sendCommand({"RequestOutput": "Off"})

    def setAwayActionToOff(self, enable: bool = True):
        """
        Set the away mode action of the smart plug
        param enable: true = turn off when away mode set, false = keep current state
        return: boolean
        """
        if enable:
            return self._sendCommand({"AwayAction": "Off"})
        else:
            return self._sendCommand({"AwayAction": "NoChange"})


class _wiserRoom:
    """ Class representing a Wiser Room entity """
    def __init__(self, data: dict, schedule: _wiserSchedule, devices: _wiserDevice):
        self.boostEndTime = 0
        self.boostTimeRemaining = 0
        self.currentTargetTemperature = _fromWiserTemp(data.get("CurrentSetPoint", TEMP_MINIMUM))
        self.currentTemperature = _fromWiserTemp(data.get("CalculatedTemperature", TEMP_MINIMUM))
        self.devices = devices
        self.id = data.get("id")
        self.isBoosted = True if data.get("Override", False) else False
        self.isHeating = True if data.get("ControlOutputState", "Off") == "On" else False
        self.mode = data.get("Mode")        
        self.name = data.get("Name")
        self.percentageDemand = data.get("PercentageDemand", 0)
        self.schedule = schedule
        self.scheduleId = data.get("ScheduleId")
        self.scheduledTargetTemperature = _fromWiserTemp(data.get("ScheduledSetPoint",TEMP_MINIMUM))
        self.temperatureSettingOrigin = data.get("SetpointOrigin", "Unknown")
        self.windowDetectionActive = data.get("WindowDetectionActive", "Unknown")
        self.windowState = data.get("WindowState","Unknown")

    def _sendCommand(self, cmd: dict):
        """
        Send control command to the room
        param cmd: json command structure
        return: boolen - true = success, false = failed
        """
        rest = _wiserRestController()
        return rest._sendCommand(WISERROOM.format(self.id), cmd)

    def setWindowDetectionActive(self, enabled: bool = False):
        """
        Set the window detection setting of the room
        param enabled: turn on or off window detection
        return: boolean
        """
        return self._sendCommand({"WindowDetectionActive": enabled})

    def setModeAuto(self):
        """
        Set the mode to auto setting of the room
        return: boolean
        """
        return self._sendCommand({"Mode": "Auto"})

    def setModeManual(self):
        """
        Set the mode to manual setting of the room
        return: boolean
        """
        return self._sendCommand({"Mode": "Manual"})

    def setModeOff(self):
        """
        Set the mode to off setting of the room
        return: boolean
        """
        self.setModeManual()
        self.setTemperature(TEMP_OFF)
    
    def setBoost(self, incTemp: float, duration: int):
        """
        Boost the temperature of the room
        param incTemp: increase target temperature over current temperature by 0C to 5C
        param duration: the duration to boost the room temperature in minutes
        return: boolean
        """
        return self._sendCommand({
            "RequestOverride": {
                "Type": "Boost",
                "DurationMinutes": duration,
                "IncreaseSetPointBy": _toWiserTemp(incTemp) if _toWiserTemp(incTemp) <= MAX_BOOST_INCREASE else MAX_BOOST_INCREASE
            }
        })

    def cancelBoost(self):
        """
        Cancel the temperature boost of the room
        return: boolean
        """
        #TODO - cancel boost if boosted.  Need to check self.isBoosted
        return self.cancelOverride()

    def setTemperature(self, temp: float):
        """
        Set the temperature of the room to override current schedule temp or in manual mode
        param temp: the temperature to set in C
        return: boolean
        """
        return self._sendCommand({
            "RequestOverride": {
                "Type": "Manual",
                "SetPoint": _toWiserTemp(_validateTemperature(temp)),
            }
        })

    def setTemperatureForDuration(self, temp: float, duration: int):
        """
        Set the temperature of the room to override current schedule temp or in manual mode
        param temp: the temperature to set in C
        return: boolean
        """
        return self._sendCommand({
            "RequestOverride": {
                "Type": "Manual",
                "DurationMinutes": duration,
                "SetPoint": _toWiserTemp(_validateTemperature(temp)),
            }
        })
 
    def scheduleAdvance(self):
        """
        Advance room schedule to the next scheduled time and temperature setting
        return: boolean
        """
        return self._sendCommand({
            "RequestOverride": {
                "Type": "Manual",
                "SetPoint": _toWiserTemp(
                    _validateTemperature(
                        _fromWiserTemp(self.schedule.next.get("DegreesC"))
                    )
                ),
            }
        })
        

    def cancelOverride(self):
        """
        Set room schedule to the current scheduled time and temperature setting
        return: boolean
        """
        return self._sendCommand({
            "RequestOverride": {
                "Type": "None"
            }
        })

    def setName(self, name: str):
        """
        Set the name of the room
        param name: name to call the room
        """
        return self._sendCommand({"Name": name.title()})


class _wiserHeating:
    """ Class representing a Wiser Heating Channel """
    #TODO - Do we need this???
    def __init__(self, data: dict):
        return None


class _wiserHotwater:
    """ Class representing a Wiser Hot Water controller """
    def __init__(self, data: dict, schedule: dict):
        self.currentControlSource = data.get("HotWaterDescription", "Unknown")
        self.id = data.get("id")
        self.ignoreAwayMode = data.get("AwayModeSuppressed","Unkown")
        self.isHeating = True if data.get("WaterHeatingState") == "On" else False
        self.isBoosted = True if data.get("Override") else False
        self.mode = data.get("Mode")
        self.schedule = schedule

    def _sendCommand(self, cmd: dict):
        """
        Send control command to the hot water
        param cmd: json command structure
        return: boolen - true = success, false = failed
        """
        rest = _wiserRestController()
        return rest._sendCommand(WISERHOTWATER.format(self.id), cmd)

    def turnOn(self):
        """
        Turn on hotwater.  In auto this is until next schedule event.  In manual modethis is on until changed.
        return: boolean
        """
        return self._sendCommand({
            "RequestOverride": {
                "Type": "Manual",
                "SetPoint": _toWiserTemp(HW_ON)
            }
        })

    def turnOff(self):
        """
        Turn off hotwater.  In auto this is until next schedule event.  In manual modethis is on until changed.
        return: boolean
        """
        return self._sendCommand({
            "RequestOverride": {
                "Type": "Manual",
                "SetPoint": _toWiserTemp(HW_OFF)
            }
        })

    def setModeAuto(self):
        """
        Set the mode to auto setting of the hot water
        return: boolean
        """
        return self._sendCommand({"Mode": "Auto"})

    def setModeManual(self):
        """
        Set the mode to manual setting of the hotwater
        return: boolean
        """
        return self._sendCommand({"Mode": "Manual"})

    def setOverrideOn(self, duration: int):
        """
        Boost the hot water for x minutes
        param temp: the boost temperature to set in C
        param duration: the duration to boost the room temperature in minutes
        return: boolean
        """
        return self._sendCommand({
            "RequestOverride": {
                "Type": "Manual",
                "DurationMinutes": duration,
                "SetPoint": _toWiserTemp(HW_ON),
                "Originator": "App",
            }
        })

    def setOverrideOff(self, duration: int):
        """
        Boost the hot water for x minutes
        param temp: the boost temperature to set in C
        param duration: the duration to boost the room temperature in minutes
        return: boolean
        """
        return self._sendCommand({
            "RequestOverride": {
                "Type": "Manual",
                "DurationMinutes": duration,
                "SetPoint": _toWiserTemp(HW_OFF),
                "Originator": "App",
            }
        })

    def cancelOverride(self):
        """
        Cancel the boost of the hot water
        return: boolean
        """
        return self._sendCommand({
            "RequestOverride": {
                "Type": "None"
            }
        })


"""
Support Classess
"""
class _wiserNetwork:
    """ Data structure for network information for a Wiser Hub """
    def __init__(self, data: dict):
        
        self.SSID = data.get("SSID", "Unknown")
        self.securityMode = data.get("SecurityMode", "Unknown")
        self.macAddress = data.get("MacAddress", "Unknown")

        self.hostname = data.get("NetworkInterface",{}).get("HostName", "Unknown")
        self.dhcpMode = data.get("NetworkInterface",{}).get("DhcpMode", "Unknown")

        self.rssi = data.get("RSSI", {}).get("Current", "Unknown")
        self.signalPercent = min(100,int(2*(self.rssi + 100)))

        self.ipAddress = (
            data.get("DhcpStatus",{}).get("IPv4Address", "Unknown") 
            if self.dhcpMode == "Client" 
            else data.get("NetworkInterface",{}).get("IPv4HostAddress", "Unknown")
        )

        self.ipSubnetMask = (
            data.get("DhcpStatus",{}).get("IPv4SubnetMask", "Unknown") 
            if self.dhcpMode == "Client" 
            else data.get("NetworkInterface",{}).get("IPv4SubnetMask", "Unknown")
        )

        self.ipGateway = (
            data.get("DhcpStatus",{}).get("IPv4DefaultGateway", "Unknown") 
            if self.dhcpMode == "Client" 
            else data.get("NetworkInterface",{}).get("IPv4DefaultGateway", "Unknown")
        )

        self.ipPrimaryDNS = (
            data.get("DhcpStatus",{}).get("IPv4PrimaryDNS", "Unknown") 
            if self.dhcpMode == "Client" 
            else data.get("NetworkInterface",{}).get("IPv4PrimaryDNS", "Unknown")
        )

        self.ipSecondaryDNS = (
            data.get("DhcpStatus",{}).get("IPv4SecondaryDNS", "Unknown") 
            if self.dhcpMode == "Client" 
            else data.get("NetworkInterface",{}).get("IPv4SecondaryDNS", "Unknown")
        )


class _wiserCloud:
    """ Data structure for cloud information for a Wiser Hub """
    def __init__(self, cloudStatus: str, data: dict):
        self.connectionStatus = cloudStatus
        self.environment = data.get("Environment")
        self.detailedPublishing = data.get("DetailedPublishing")
        self.enableDiagnosticTelemetry = data.get("EnableDiagnosticTelemetry")
        self.wiserApiHost = data.get("WiserApiHost")
        self.bootStrapApiHost = data.get("BootStrapApiHost")


class _wiserBattery:
    """ Data structure for battery information for a Wiser device that is powered by batteries """
    def __init__(self, data: dict):
        self.voltage = data.get("BatteryVoltage",0)/10
        self.level = data.get("BatteryLevel","NoBattery")
        self.percent = -1

        if data.get("ProductType") == "RoomStat":
            self.percent = min(100, int(
                    (
                        (self.voltage - ROOMSTAT_MIN_BATTERY_LEVEL)
                        / (ROOMSTAT_FULL_BATTERY_LEVEL - ROOMSTAT_MIN_BATTERY_LEVEL)
                    )  * 100
                )
            )

        if data.get("ProductType") == "iTRV":
            self.percent = min(100, int(
                    (
                        (self.voltage - TRV_MIN_BATTERY_LEVEL)
                        / (TRV_FULL_BATTERY_LEVEL - TRV_MIN_BATTERY_LEVEL)
                    )
                    * 100
                )
            )


class _wiserSignal:
    """ Data structure for zigbee signal information for a Wiser device """
    def __init__(self, data: dict):
        self.displayedSignalStrength = data.get("DisplayedSignalStrength")        
        self.controllerRssi = data.get("ReceptionOfController",{"Rssi":0}).get("Rssi")
        self.controllerLqi = data.get("ReceptionOfController",{"Lqi":0}).get("Lqi")
        self.controllerSignalPercent = min(100,int(2*(self.controllerRssi + 100)))
        self.deviceRssi = data.get("ReceptionOfDevice",{"Rssi":0}).get("Rssi")
        self.deviceLqi = data.get("ReceptionOfDevice",{"Lqi":0}).get("Lqi")
        self.deviceSignalPercent = min(100,int(2*(self.deviceRssi + 100)))


class _wiserGPS:
    """ Data structure for gps positional information for a Wiser Hub """
    def __init__(self, data: dict):
        self.latitude = data.get("Latitude")
        self.longitude = data.get("Longitude")




def _validateTemperature(temp: float):
    """
    Validates temperature value is in range of Wiser Hub allowed values
    Sets to min or max temp if value exceeds limits
    param temp: temperature value to validate
    return: float
    """
    if (temp > TEMP_MAXIMUM):
        return TEMP_MAXIMUM
    elif (temp < TEMP_MINIMUM and temp != TEMP_OFF):
        return TEMP_MINIMUM
    else:
        return temp

def _toWiserTemp(temp: float):
    """
    Converts from temperature to wiser hub format
    param temp: The temperature to convert
    return: Integer
    """
    temp = int(temp * 10)
    return temp

def _fromWiserTemp(temp: int):
    """
    Conerts from wiser hub temperature format to decimal value
    param temp: The wiser temperature to convert
    return: Float
    """
    if temp is not None:
        temp = round(temp / 10, 1)
    return temp