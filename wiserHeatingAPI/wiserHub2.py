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

import logging
import requests
import json
import sys
from time import sleep
from typing import cast
from zeroconf import ServiceBrowser, ServiceStateChange, Zeroconf

__VERSION__ = "2.0.0"

# Temperature Constants
TEMP_MINIMUM = 5
TEMP_MAXIMUM = 30
TEMP_OFF = -20
DEFAULT_AWAY_MODE_TEMP = 10.5
DEFAULT_DEGRADED_TEMP = 18
HW_ON = 110
HW_OFF = -20
MAX_BOOST_INCREASE = 5

# Battery Constants
TRV_FULL_BATTERY_LEVEL = 3.0
TRV_MIN_BATTERY_LEVEL = 2.5
ROOMSTAT_MIN_BATTERY_LEVEL = 1.7
ROOMSTAT_FULL_BATTERY_LEVEL = 2.7

# Other Constants
REST_TIMEOUT = 15
MDNS_TIMEOUT = 10
TRACEBACK_LIMIT = 3

# Wiser Hub Rest Api URL Constants
WISERHUBURL         = "http://{}/data/v2/"
WISERHUBDOMAIN      = WISERHUBURL + "/domain/"
WISERHUBNETWORK     = WISERHUBURL + "/network/"
WISERHUBSCHEDULES   = WISERHUBURL + "/schedules/"
WISERHUBSYSTEM      = WISERHUBDOMAIN + "System/"
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
        self.wiserIP = None
        self.wiserSecret = None
        self.wiserHubName = None

_wiserApiConnection = _wiserConnection()

class wiserAPI():
    """ Main api class to access all entities and attributes of wiser system """
    def __init__(self, hubIP: str, secret: str):
        _wiserApiConnection.wiserIP = hubIP
        _wiserApiConnection.wiserSecret = secret
        _wiserApiConnection.wiserHubName = ""
        
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

        # Do hub discovery if null IP is passed when initialised
        if _wiserApiConnection.wiserIP is None:
            wiserDiscover = _wiserDiscover()
            if wiserDiscover._discoverHub():
                print("Hub: {}, IP: {}".format(_wiserApiConnection.wiserHubName, _wiserApiConnection.wiserIP))
            else:
                print("No Wiser hub discovered on network")

        # Read hub data if hub IP and secret exist
        if _wiserApiConnection.wiserIP is not None and _wiserApiConnection.wiserSecret is not None:
            self.readHubData()  
            #TODO - Add validation function to check for no devices, rooms etc here.      
        else:
            print("No connection info")

    
    def readHubData(self):
        """ Read all data from hub """
        def _getDomainData(hubData):
            url = WISERHUBDOMAIN.format(_wiserApiConnection.wiserIP)
            return hubData._getHubData(url)

        def _getNetworkData(hubData):
            url = WISERHUBNETWORK.format(_wiserApiConnection.wiserIP)
            return hubData._getHubData(url)

        def _getScheduleData(hubData):
            url = WISERHUBSCHEDULES.format(_wiserApiConnection.wiserIP)
            return hubData._getHubData(url)
    
    
        # Read hub data endpoints
        hubData = _wiserRestController()
        self.domainData = _getDomainData(hubData)
        self.networkData = _getNetworkData(hubData)
        self.scheduleData = _getScheduleData(hubData)
        
        # Schedules
        self.schedules = []
        for scheduleType in ["Heating","OnOff"]:
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
        self.rooms = [
            _wiserRoom(
                room, 
                self.getScheduleById(room.get("ScheduleId")),
                [device for device in self.devices if (device.id in room.get("SmartValveIds",["0"]) or device.id == room.get("RoomStatId","0"))]
            ) for room in self.domainData.get("Room")
        ]

        # Hot Water
        self.hotwater = _wiserHotwater(
            self.domainData.get("Hotwater",{}),
            self.getScheduleById(self.domainData.get("Hotwater",{}).get("ScheduleId",0)),
        )

        # Heating
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
            "SECRET": _wiserApiConnection.wiserSecret,
            "Content-Type": "application/json;charset=UTF-8",
        }

    def _getHubData(self, url: str):
        """
        Read data from hub and raise errors if fails
        param url: url of hub rest api endpoint
        return: json object
        """
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

    def _sendCommand(self, url: str, patchData: dict):
        """
        Send control command to hub and raise errors if fails
        param url: url of hub rest api endpoint
        param patchData: json object containing command and values to set
        return: boolean
        """
        url = WISERHUBDOMAIN.format(_wiserApiConnection.wiserIP) + url
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


class _wiserDiscover:
    """ Class to handle mDns discovery of a wiser hub on local network """
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
                    _wiserApiConnection.wiserIP = addresses[0].replace(":80","")
                    _wiserApiConnection.wiserHubName = info.server.replace(".local.","")

    def _discoverHub(self):
        """
        Call zeroconf service browser until hub found or timeout
        return: boolean - true = hub found, false = hub not found
        """
        timeout = 0

        zeroconf = Zeroconf()
        services = ["_http._tcp.local."]
        ServiceBrowser(zeroconf, services, handlers=[self._zeroconf_on_service_state_change])

        while _wiserApiConnection.wiserIP is None and timeout < MDNS_TIMEOUT * 10:
            sleep(0.1)
            timeout += 1
        zeroconf.close()

        if _wiserApiConnection.wiserIP is not None:
            return True
        return False


class _wiserSchedule:
    """
    Class representing a wiser Schedule
    """
    def __init__(self, scheduleType: str, scheduleData: dict):
        self.type = scheduleType
        self.id = scheduleData.get("id")
        self.name = scheduleData.get("Name")
        self.next = scheduleData.get("Next")
        self.currentTargetTemperature = _fromWiserTemp(scheduleData.get("CurrentSetPoint", TEMP_OFF))
        self.currentState = scheduleData.get("CurrentState")
        self.scheduleData = scheduleData

    def setSchedule(self, scheduleData: dict):
        """
        Set new schedule
        param scheduleData: json data respresenting a schedule
        return: boolen - true = successfully set, false = failed to set
        """
        raise WiserNotImplemented

    def copySchedule(self, toId: int):
        """
        Copy this schedule to another schedule
        param toId: id of schedule to copy to
        return: boolen - true = successfully set, false = failed to set
        """
        raise WiserNotImplemented


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


class _wiserHub:
    """ Class representing a Wiser Hub device """
    def __init__(self, data: dict, deviceData: dict, networkData: dict, cloudData: dict):
        self.pairingStatus = data.get("PairingStatus")
        self.timezoneOffset = data.get("TimeZoneOffset")
        self.automaticDaylightSaving = data.get("AutomaticDaylightSaving")
        self.systemMode = data.get("SystemMode")
        self.fotaEnabled = data.get("FotaEnabled")  # firmware over the air
        self.activeFirmware = data.get("ActiveSystemVersion")
        self.brandName = data.get("BrandName")
        self.hubTime = data.get("LocalDateAndTime")
        self.openThermConnectionStatus = data.get("OpenThermConnectionStatus", "Disconnected")
        self.boilerFuelType = data.get("BoilerSettings", {"FuelType":"Unknown"}).get("FuelType")
        self.heatingButtonOverrideState = data.get("HeatingButtonOverrideState")
        self.hotWaterButtonOverrideState = data.get("HotWaterButtonOverrideState")
        self.userOverridesActive = data.get("UserOverridesActive", False)
        self.valveProtectionEnabled = data.get("ValveProtectionEnabled", False)
        self.ecoModeEnabled = data.get("EcoModeEnabled", False)
        self.comfortModeEnabled = data.get("ComfortModeEnabled", False)
        self.awayModeAffectsHotWater = data.get("AwayModeAffectsHotWater", False)
        self.awayModeTargetTemperature = data.get("AwayModeSetPointLimit", 0)
        self.degradedModeTargetTemperature = data.get("DegradedModeSetpointThreshold",0)
        self.userOverridesActive = data.get("UserOverridesActive", False)
        self.geoPosition = _wiserGPS(data.get("GeoPosition", {}))
        self.cloud = _wiserCloud(data.get("CloudConnectionStatus"), cloudData)
        self.network = _wiserNetwork(networkData.get("Station", {}))

    def _sendCommand(self, cmd: dict) -> bool:
        """
        Send system control command to Wiser Hub
        param cmd: json command structure
        return: boolen - true = success, false = failed
        """
        rest = _wiserRestController()
        return rest._sendCommand(WISERHUBSYSTEM, cmd)

    def setTime(self, unixTime: int):
        """
        Set the time on the wiser hub
        param unixTime: the unix time valeu to set
        return: boolen - true = success, false = failed
        """
        raise WiserNotImplemented

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
        return self._sendCommand({"AwayModeAffectsHotWater": enabled})

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
        return self._sendCommand({
            "RequestOverride":{
                "type": 2 if enabled else 0
                }
            })


class _wiserSmartValve(_wiserDevice):
    """ Class representing a Wiser Smart Valve device """
    def __init__(self, data: dict, deviceTypeData: dict):
        super().__init__(data)
        self.mountingOrientation = deviceTypeData.get("MountingOrientation")
        self.currentTargetTemperature = _fromWiserTemp(deviceTypeData.get("SetPoint"))
        self.currentTemperature = _fromWiserTemp(deviceTypeData.get("MeasuredTemperature"))
        self.percentageDemand = deviceTypeData.get("PercentageDemand")
        self.windowState = deviceTypeData.get("WindowState")
        self.deviceLockEnabled = data.get("DeviceLockEnabled", False)
        self.battery = _wiserBattery(data)

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
        self.currentTargetTemperature = _fromWiserTemp(deviceTypeData.get("SetPoint"))
        self.currentTemperature = _fromWiserTemp(deviceTypeData.get("MeasuredTemperature"))
        self.currentHumidity = deviceTypeData.get("MeasuredHumidity")
        self.deviceLockEnabled = data.get("DeviceLockEnabled", False)
        self.battery = _wiserBattery(data)

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
        self.name = deviceTypeData.get("Name", "Unknown")
        self.schedule = schedule
        self.mode = deviceTypeData.get("Mode", "Unknown")
        self.controlSource = deviceTypeData.get("ControlSource", "Unknown")
        self.awayAction = deviceTypeData.get("AwayAction", "Unknown")
        self.currentState = deviceTypeData.get("OutputState", "Unknown")
        self.scheduledState = deviceTypeData.get("ScheduledState", "Unknown")
        self.manualState = deviceTypeData.get("ManualState", "Unknown")

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
        self.id = data.get("id")
        self.name = data.get("Name")
        self.mode = data.get("Mode")
        self.currentTemperature = _fromWiserTemp(data.get("CalculatedTemperature", TEMP_MINIMUM))
        self.currentTargetTemperature = _fromWiserTemp(data.get("CurrentSetPoint", TEMP_MINIMUM))
        self.scheduledTargetTemperature = _fromWiserTemp(data.get("ScheduledSetPoint",TEMP_MINIMUM))
        self.temperatureSettingOrigin = data.get("SetpointOrigin", "Unknown")
        self.isBoosted = True if data.get("Override", False) else False
        self.boostEndTime = 0
        self.percentageDemand = data.get("PercentageDemand", 0)
        self.isHeating = True if data.get("ControlOutputState", "Off") == "On" else False
        self.windowDetectionActive = data.get("WindowDetectionActive", "Unknown")
        self.windowState = data.get("WindowState","Unknown")
        self.scheduleId = data.get("ScheduleId")
        self.schedule = schedule
        self.devices = devices

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
        return self.cancelOverride()

    def getBoostTimeRemaining(self):
        """
        Get reminaing minutes of boost for the room
        return: int
        """
        raise WiserNotImplemented

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
        print("heating initiated")


class _wiserHotwater:
    """ Class representing a Wiser Hot Water controller """
    def __init__(self, data: dict, schedule: dict):
        self.id = data.get("id")
        self.mode = data.get("Mode")
        self.isHeating = True if data.get("WaterHeatingState") == "On" else False
        self.isBoosted = True if data.get("Override") else False
        self.schedule = schedule
        #TODO: Add rest here

    def _sendCommand(self, cmd: dict):
        """
        Send control command to the hot water
        param cmd: json command structure
        return: boolen - true = success, false = failed
        """
        rest = _wiserRestController()
        return rest._sendCommand(WISERHOTWATER.format(self.id), cmd)

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
                "Type": "None",
                "DurationMinutes": 0,
                "SetPoint": 0,
                "Originator": "App",
            }
        })

    def setSchedule(self, scheduleData: dict):
        return WiserNotImplemented



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
    temp = round(temp / 10, 1)
    return temp