from wiserHeatingAPI import wiserHub2
from datetime import datetime
import logging

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
    wh = wiserHub2.wiserAPI(wiserip, wiserkey)
    # wh = wiserHub2.wiserAPI(None, wiserkey)   # Connect to hub with discovery

    # Iterate through wiser entity objects
    # Main data stores
    if not wh.domainData:
        raise Exception("No data in domainData")
    else:
        print("Domain data read")

    if not wh.networkData:
        raise Exception("No data in networkData")
    else:
        print("Network data read")

    if not wh.scheduleData:
        raise Exception("No data in scheduleData")
    else:
        print("Schedule data read")
    
    success("Hub connection and data test successful")



    # Entity objects
    # ----------------------------------
    # Hub
    # ----------------------------------
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

        success("Rooms data and controls test successful")


    # ----------------------------------
    # Schedules
    # ----------------------------------
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














    
except Exception as ex:
    fail("Exception error during tests")
    raise




