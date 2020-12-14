from wiserHeatingAPI import wiserHub2
from datetime import datetime
import logging

USE_DISCOVERY = True


TEST_HUB = False
TEST_ROOMS = False
TEST_SCHEDULES = False
TEST_DEVICES = False
TEST_HOTWATER = True

class bcolors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"

_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(logging.DEBUG)

# Get wiserkey/hubIp from wiserkeys.params file
# This file is not source controlled as it contains the testers secret etc
with open("wiserkeys.params", "r") as f:
    data = f.read().split("\n")
wiserkey = ""
wiserip = ""

for lines in data:
    line = lines.split("=")
    if line[0] == "wiserkey":
        wiserkey = line[1]
    if line[0] == "wiserhubip":
        wiserip = line[1]

def printLine():
    print("--------------------------------------------------------")

def testStart(title: str):
    printLine()
    print(bcolors.OKCYAN + "Testing - " + title + bcolors.ENDC)
    printLine()

def printl(title: str, value, value2 = ""):
    print(bcolors.OKBLUE + title + ":" + bcolors.ENDC, value, value2)

def success(msg: str):
    printLine()
    print(bcolors.OKGREEN + msg + bcolors.ENDC)
    printLine()
    for i in range(2):
        print("")

def fail(msg: str):
    printLine()
    print(bcolors.FAIL + msg + bcolors.ENDC)
    printLine()
    for i in range(2):
        print("")



# Test hub discovery
testStart("Auto Discovery")
d = wiserHub2.wiserDiscovery()
hubs = d.discoverHub()
if not hubs:
    fail("No wiser hub discovered")
    raise Exception
else:
    for hub in hubs:
        print("Discovered hub {} with ip {}".format(hub["name"], hub["ip"]))
    success("Hub discovery successful")




try:
    testStart("Hub Connection and Data Reading")
    # Connect to hub with hostname
    
    if USE_DISCOVERY:
        # use mDns discovery to find hub
        wh = wiserHub2.wiserAPI(None, wiserkey)
    else:
        # Connect to hub with host name or IP
        wh = wiserHub2.wiserAPI(wiserip, wiserkey) 
    
    printl("Using hub discovery", USE_DISCOVERY)
    printl("Connected to hub " + wh.hub.name, wh.hub.network.ipAddress)

    # Iterate through wiser entity objects
    # Main data stores
    if not wh.domainData:
        raise Exception("No data in domainData")
    else:
        printl("Domain data","Success")

    if not wh.networkData:
        raise Exception("No data in networkData")
    else:
        printl("Network data", "Success")

    if not wh.scheduleData:
        raise Exception("No data in scheduleData")
    else:
        printl("Schedule data", "Success")
    
    success("Hub connection and data test successful")



    # Entity objects
    # ----------------------------------
    # Hub
    # ----------------------------------
    if TEST_HUB:
        testStart("Hub Data and Controls")
        h = wh.hub
        printl("Active firmware", h.activeFirmware)
        printl("Auto daylight saving", h.automaticDaylightSaving)
        printl("Away mode affects hot water", h.awayModeAffectsHotWater)
        printl("Away mode target temp", h.awayModeTargetTemperature)
        printl("Boiler fuel type", h.boilerFuelType)
        printl("Brand name", h.brandName)
        printl("Comfort mode enabled", h.comfortModeEnabled)
        printl("Degraded target temp", h.degradedModeTargetTemperature)
        printl("Eco mode enabled", h.ecoModeEnabled)
        printl("Firmware over the air enabled", h.fotaEnabled)
        printl("Geo position", h.geoPosition.latitude, h.geoPosition.longitude)
        printl("Heating button override", h.heatingButtonOverrideState)
        printl("Hot water button override", h.hotWaterButtonOverrideState)
        printl("Hub date and time", h.hubTime)
        printl("Hub name", h.name)
        printl("Opentherm connection status", h.openThermConnectionStatus)
        printl("Pairing status", h.pairingStatus)
        printl("System mode", h.systemMode)
        printl("tTimezone offset", h.timezoneOffset)
        printl("User override active", h.userOverridesActive)
        printl("Valve protection enabled", h.valveProtectionEnabled)

        # Network
        printl("Network SSID", h.network.SSID)
        printl("Network security mode", h.network.securityMode)
        printl("Network mac address", h.network.macAddress)
        printl("Network hostname", h.network.hostname)
        printl("Network dchp mode", h.network.dhcpMode)
        printl("Network rssi", h.network.rssi)
        printl("Network signal strength", h.network.signalPercent)
        printl("Network ip address", h.network.ipAddress)
        printl("Network subnet mask", h.network.ipSubnetMask)
        printl("Network default gateway", h.network.ipGateway)
        printl("Network primary dns", h.network.ipPrimaryDNS)
        printl("Network secondary dns", h.network.ipSecondaryDNS)

        # Cloud
        printl("Cloud connection", h.cloud.connectionStatus)
        printl("Cloud environment", h.cloud.environment)
        printl("Cloud detailed publishing", h.cloud.detailedPublishing)
        printl("Cloud diagnostic telemetry", h.cloud.enableDiagnosticTelemetry)
        printl("Cloud api host", h.cloud.wiserApiHost)
        printl("Cloud bootstrap Api host", h.cloud.bootStrapApiHost)

        # Controls
        printl("Set time",h.setTime(int(datetime.utcnow().timestamp())))
        printl("Set valve protection",h.setValveProtection(h.valveProtectionEnabled))
        printl("Set eco mode", h.setEcoMode(h.ecoModeEnabled))
        printl("Set comfort mode", h.setComfortMode(h.comfortModeEnabled))
        printl("Set away mode affects hot water", h.setAwayModeAffectsHotWater(h.awayModeAffectsHotWater))
        printl("Set away mode target temp", h.setAwayModeTargetTemperature(h.awayModeTargetTemperature))
        printl("Set degraded mode temp", h.setDegradedModeTargetTemperature(h.degradedModeTargetTemperature))
        printl("Set away mode", h.setAwayMode(False))

        h = None
        success("Hub data and controls test successful")


    # ----------------------------------
    # Rooms
    # ----------------------------------
    if TEST_ROOMS:
        testStart("Rooms data and controls")
        if len(wh.rooms) == 0:
            fail("No rooms found on hub")
        else:
            for room in wh.rooms:
                print("---------------------")
                printl("Room name", room.name)
                print("---------------------")
                printl("Boost end time", room.boostEndTime)
                printl("Current temp", room.currentTemperature)
                printl("Current target remp", room.currentTargetTemperature)
                printl("Id", room.id)
                printl("Is boosted", room.isBoosted)
                printl("Is heating", room.isHeating)
                printl("Mode", room.mode)
                printl("Percentage demand", room.percentageDemand)
                printl("Schedule Id", room.scheduleId)
                printl("Scheduled target temp", room.scheduledTargetTemperature)
                printl("Temp setting origin", room.temperatureSettingOrigin)
                printl("Window detection active", room.windowDetectionActive)
                printl("Window state", room.windowState)

                # Room Devices
                for rd in room.devices:
                    printl("Device type", rd.productType)
                    printl("  Device id", rd.id)
                    printl("  Device signal", str(rd.signal.deviceSignalPercent) + "%")

                # Schedule
                printl("Schedule type", room.schedule.type)
                printl("  Schedule name", room.schedule.name)
                printl("  Schedule target temp", room.schedule.currentTargetTemperature)
                printl("  Schedule next setting", room.schedule.next)

            # Use first room for controls tests
            roomName =  wh.getRoomById(1).name
            printl("Control test room (room id 1)", roomName)

            room = wh.getRoomByName(roomName)

            printl("  Set window detection", room.setWindowDetectionActive(room.windowDetectionActive))
            printl("  Set mode auto", room.setModeAuto())
            printl("  Set mode manual", room.setModeManual())
            printl("  Set mode off", room.setModeOff())
            printl("  Set boost", room.setBoost(2, 30))
            printl("  Cancel boost", room.cancelBoost())
            printl("  Set room temp", room.setTemperature(20))
            printl("  Set room temp for 60 mins", room.setTemperatureForDuration(19,60))
            printl("  Schedule advance", room.scheduleAdvance())
            printl("  Cancel all overrides", room.cancelOverride())
            printl("  Set room name", room.setName(roomName))

            # Set room back to auto
            room.setModeAuto()

            success("Rooms data and controls test successful")


    # ----------------------------------
    # Schedules
    # ----------------------------------
    if TEST_SCHEDULES:
        testStart("Schedule data and controls")
        if len(wh.schedules) == 0:
            fail("No schedules found on hub")
        else:
            schedule = wh.schedules[0]

            printl("Schedule type", schedule.type)
            printl("Schedule id", schedule.id)
            printl("Schedule name", schedule.name)
            printl("Schedule next event", schedule.next)
            if schedule.type == "Heating":
                printl("Schedule current target temp", schedule.currentTargetTemperature)
            else:
                printl("Schedule current state", schedule.currentState)

            # Control tests
            printl("Saving json schedule to file - schedule.json", schedule.saveScheduleToFile("schedule.json"))
            printl("Saving yaml schedule to file - schedule.yaml", schedule.saveScheduleToFileYaml("schedule.yaml"))
            printl("Set schedule from data", schedule.setSchedule(schedule.scheduleData))
            printl("Set schedule from json file", schedule.setScheduleFromFile("schedule.json"))
            printl("Set schedule from yaml file", schedule.setScheduleFromYamlFile("schedule.yaml"))

            # Test schedule copy if more than 1 room exists
            if len(wh.rooms) >= 2:
                # Keep room2 schedule data to put back
                rm2schedule = wh.rooms[1].schedule.scheduleData

                printl("Copying " + wh.rooms[0].name + " schedule to " + wh.rooms[1].name, schedule.copySchedule(wh.rooms[1].schedule.id))
                printl("Reset " + wh.rooms[1].name + " to previous schedule", wh.rooms[1].schedule.setSchedule(rm2schedule))

            success("Schedule data and controls test successful")

    # ----------------------------------
    # Devices
    # ----------------------------------
    if TEST_DEVICES:
        testStart("Device data and controls")
        if len(wh.devices) == 0:
            fail("No devices (smart valves, smart plugs or room stats) found on hub")
        else:
            for device in wh.devices:
                print("---------------------")
                printl("Device id", device.id)
                printl("Device type", device.productType)
                print("---------------------")
                printl("Device node id", device.nodeId)
                printl("Device model", device.modelIdentifier)
                printl("Device firmware version", device.firmwareVersion)
                printl("Device serial no", device.serialNo)
                printl("Device parent node id", device.parentNodeId)
                printl("Device parent node type", wh.getDeviceByNodeId(device.parentNodeId).productType)
                # If parent device is not controller then get name of parent device
                if device.parentNodeId != 0:
                    printl("Device parent name", wh.getSmartPlugById(wh.getDeviceByNodeId(device.parentNodeId).id).name)
                else:
                    printl("Device parent name", wh.getDeviceByNodeId(device.parentNodeId).productType)

                printl("Device signal strength", device.signal.deviceSignalPercent)
                printl("Device signal strength description", device.signal.displayedSignalStrength)

                if device.productType == "iTRV":
                    sv = wh.getSmartValveById(device.id)
                    printl("Device battery percent", sv.battery.percent)
                    printl("Device battery level", sv.battery.level)
                    printl("Device battery voltage", sv.battery.voltage)
                    printl("Device target temp", sv.currentTargetTemperature)
                    printl("Device current temp", sv.currentTemperature)
                    printl("Device lock enabled", sv.deviceLockEnabled)
                    printl("Device orientation", sv.mountingOrientation)
                    printl("Device percentage demand", sv.percentageDemand)
                    # Commands
                    printl("Set device lock to false", sv.deviceLock(False))
                    printl("Set indentify to false", sv.identify(False))

                if device.productType == "RoomStat":
                    rs = wh.getRoomStatById(device.id)
                    printl("Device battery percent", rs.battery.percent)
                    printl("Device battery level", rs.battery.level)
                    printl("Device battery voltage", rs.battery.voltage)
                    printl("Device target temp", rs.currentTargetTemperature)
                    printl("Device current temp", rs.currentTemperature)
                    printl("Device current humidity", rs.currentHumidity)
                    printl("Device lock enabled", rs.deviceLockEnabled)
                    # Commands
                    printl("Set device lock to false", rs.deviceLock(False))
                    printl("Set indentify to false", rs.identify(False))

                if device.productType == "SmartPlug":
                    sp = wh.getSmartPlugById(device.id)
                    printl("Device away action", sp.awayAction)
                    printl("Device control source", sp.controlSource)
                    printl("Device current state", sp.currentState)
                    printl("Device manual state", sp.manualState)
                    printl("Device mode", sp.mode)
                    printl("Device name", sp.name)
                    printl("Device schedule state", sp.scheduledState)
                    printl("Device schedule next event", sp.schedule.next)
                    # Commands
                    printl("Set device mode to auto", sp.setModeAuto())
                    printl("Set device mode to manual", sp.setModeManual())
                    printl("Turn device on", sp.turnOn())
                    printl("Turn device off", sp.turnOff)
                    printl("Set away action to no change", sp.setAwayActionToOff(False))
                print("")

            success("Device data and controls test successful")


   
    # ----------------------------------
    # Hot Water
    # ----------------------------------
    if TEST_HOTWATER:
        testStart("Hot Water data and controls")
        if wh.hotwater is None:
            fail("Hot water not supported on this hub")
        else:
            hw = wh.hotwater
            printl("Hot water current control source", hw.currentControlSource)
            printl("Hot water id", hw.id)
            printl("Hot water ignore away mode", hw.ignoreAwayMode)
            printl("Hot water is heating", hw.isHeating)
            printl("Hot water is boosted", hw.isBoosted)
            printl("Hot water  mode", hw.mode)
            printl("Hot water schedule next event", hw.isHeating)
            # Commands
            printl("Turn hot water on", hw.turnOn())
            printl("Turn hot water off", hw.turnOff())
            printl("Set hot water mode to manual", hw.setModeManual())
            printl("Set hot water mode to auto", hw.setModeAuto)
            printl("Set on override for 10 mins", hw.setOverrideOn(10))
            printl("Set off override for 30 mins", hw.setOverrideOff(30))
            printl("Cancel overrides", hw.cancelOverride())


except wiserHub2.WiserHubAuthenticationException:
    fail("Error authenticating with wiser hub.  Check secret key!")
    
except Exception as ex:
    fail("Exception error during tests")
    raise




