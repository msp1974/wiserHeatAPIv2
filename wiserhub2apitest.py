from wiserHeatingAPI.wiserHub2 import (
    DEFAULT_AWAY_MODE_TEMP,
    DEFAULT_DEGRADED_TEMP,
    WiserAPI,
    WiserDiscovery,
    WiserModeEnum,
    WiserUnitsEmun,
    WiserAwayActionEnum,
    WiserHubAuthenticationError,
    WiserHubConnectionError,
    WiserHubRESTError,
)
from datetime import datetime
from guppy import hpy
import logging
import os
import time
import sys

USE_DISCOVERY = False
DEBUG = True

TEST_DISCOVERY = False
TEST_HUB = True
TEST_ROOMS = True
TEST_SCHEDULES = True
TEST_DEVICES = True
TEST_HOTWATER = True
TEST_HEATING = True
TEST_REFRESH = False


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


_LOGGER = logging.getLogger("wiserHeatingAPI.wiserHub2")
_LOGGER.addHandler(logging.StreamHandler(sys.stdout))
if DEBUG:
    _LOGGER.setLevel(logging.DEBUG)
else:
    _LOGGER.setLevel(logging.INFO)


h = hpy()

error_count = 0

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

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_line():
    print("--------------------------------------------------------")


def test_start(title: str):
    print_line()
    print(bcolors.OKCYAN + "Testing - " + title + bcolors.ENDC)
    print_line()


def printl(title: str, value, value2=""):
    global error_count
    if value is not None and value != "Unknown":
        print(bcolors.OKBLUE + title + ":" + bcolors.ENDC, value, value2)
    else:
        error_count += 1
        print(bcolors.OKBLUE + title + ":", bcolors.FAIL + str(value) + bcolors.ENDC, value2)


def success(msg: str):
    print_line()
    print(bcolors.OKGREEN + msg + bcolors.ENDC)
    print_line()
    for i in range(2):
        print("")


def fail(msg: str):
    print_line()
    print(bcolors.FAIL + msg + bcolors.ENDC)
    print_line()
    for i in range(2):
        print("")


# Test hub discovery
if TEST_DISCOVERY:
    test_start("Auto Discovery")
    d = WiserDiscovery()
    hubs = d.discover_hub()
    if not hubs:
        fail("No wiser hub discovered")
        raise Exception
    else:
        success("Hub discovery successful")


try:
    clear_screen()
    test_start("Hub Connection and Data Reading")
    # Connect to hub with hostname

    printl("Using hub discovery", USE_DISCOVERY)
    if USE_DISCOVERY:
        # use mDns discovery to find hub
        wh = WiserAPI(None, wiserkey, WiserUnitsEmun.imperial)
    else:
        # Connect to hub with host name or IP
        wh = WiserAPI(wiserip, wiserkey, WiserUnitsEmun.imperial)
    
    printl("Connected to hub " + wh.hub.name, wh.hub.network.ip_address)

    # Iterate through wiser entity objects
    # Main data stores
    if not wh._domain_data:
        raise Exception("No data in domainData")
    else:
        printl("Domain data", "Success")

    if not wh._network_data:
        raise Exception("No data in networkData")
    else:
        printl("Network data", "Success")

    if not wh._schedule_data:
        raise Exception("No data in scheduleData")
    else:
        printl("Schedule data", "Success")

    success("Hub connection and data test successful")

    # Entity objects
    # ----------------------------------
    # Hub
    # ----------------------------------
    if TEST_HUB:
        test_start("Hub Data and Controls")
        h = wh.hub


        printl("Active firmware", h.active_firmware_version)
        printl("Auto daylight saving enabled", h.automatic_daylight_saving_enabled)
        printl("Away mode enabled", h.away_mode_enabled)
        printl("Away mode affects hot water", h.away_mode_affects_hotwater)
        printl("Away mode target temp", h.away_mode_target_temperature)
        printl("Boiler fuel type", h.boiler_fuel_type)
        printl("Brand name", h.brand_name)
        printl("Comfort mode enabled", h.comfort_mode_enabled)
        printl("Degraded target temp", h.degraded_mode_target_temperature)
        printl("Eco mode enabled", h.eco_mode_enabled)
        printl("Firmware over the air enabled", h.firmware_over_the_air_enabled)
        printl("Geo position", h.geo_position.latitude, h.geo_position.longitude)
        printl("Heating button override", h.heating_button_override_state)
        printl("Hot water button override", h.hotwater_button_override_state)
        printl("Hub date and time", h.hub_time)
        printl("Hub name", h.name)
        printl("Opentherm connection status", h.opentherm_connection_status)
        printl("Pairing status", h.pairing_status)
        printl("System mode", h.system_mode)
        printl("Timezone offset", h.timezone_offset)
        printl("User override active", h.user_overrides_active)
        printl("Valve protection enabled", h.valve_protection_enabled)

        # Network
        printl("Network SSID", h.network.ssid)
        printl("Network security mode", h.network.security_mode)
        printl("Network mac address", h.network.mac_address)
        printl("Network hostname", h.network.hostname)
        printl("Network dchp mode", h.network.dhcp_mode)
        printl("Network rssi", h.network.signal_rssi)
        printl("Network signal strength", h.network.signal_percent)
        printl("Network ip address", h.network.ip_address)
        printl("Network subnet mask", h.network.ip_subnet_mask)
        printl("Network default gateway", h.network.ip_gateway)
        printl("Network primary dns", h.network.ip_primary_dns)
        printl("Network secondary dns", h.network.ip_secondary_dns)

        # Cloud
        printl("Cloud connection", h.cloud.connected_to_cloud)
        printl("Cloud environment", h.cloud.environment)
        printl("Cloud detailed publishing", h.cloud.detailed_publishing_enabled)
        printl("Cloud diagnostic telemetry", h.cloud.diagnostic_telemetry_enabled)
        printl("Cloud api host", h.cloud.api_host)
        printl("Cloud bootstrap Api host", h.cloud.bootstrap_api_host)

        # Controls
        printl("Set away mode to off","")
        h.away_mode_enabled = False

        printl("Set comfort mode enabled to " + str(h.comfort_mode_enabled),"")
        h.comfort_mode_enabled = h.comfort_mode_enabled

        printl("Set eco mode enabled to " + str(h.eco_mode_enabled),"")
        h.eco_mode_enabled = h.eco_mode_enabled

        printl("Set valve protection to off", "")
        h.valve_protection_enabled = False

        printl("Set away mode affects hot water", "")
        h.away_mode_affects_hotwater = True

        printl("Set away mode target temp to default", "")
        h.away_mode_target_temperature = DEFAULT_AWAY_MODE_TEMP

        printl("Set degraded temp to default", "")
        h.degraded_mode_target_temperature = DEFAULT_DEGRADED_TEMP

        h = None
        success("Hub data and controls test successful")

    # ----------------------------------
    # Rooms
    # ----------------------------------
    if TEST_ROOMS:
        test_start("Rooms data and controls")
        if len(wh.rooms) == 0:
            fail("No rooms found on hub")
        else:
            for room in wh.rooms:
                print("---------------------")
                printl("Room name", room.name)
                print("---------------------")
                printl("Boost end time", room.boost_end_time)
                printl("Boost time remaining", room.boost_time_remaining)
                printl("Current temp", room.current_temperature)
                printl("Current target remp", room.current_target_temperature)
                printl("Id", room.id)
                printl("Is boosted", room.is_boosted)
                printl("Is heating", room.is_heating)
                printl("Manual mode target temp", room.manual_target_temperature)
                printl("Mode", room.mode)
                printl("Percentage demand", room.percentage_demand)
                printl("Schedule Id", room.schedule_id)
                printl("Scheduled target temp", room.scheduled_target_temperature)
                printl("Temp setting origin", room.target_temperature_origin)
                printl("Window detection active", room.window_detection_active)
                printl("Window state", room.window_state)

                # Room Devices
                for rd in room.devices:
                    printl("Device type", rd.product_type)
                    printl("  Device id", rd.id)
                    printl("  Device signal", str(rd.signal.signal_strength) + "%")

                # Schedule
                printl("Schedule type", room.schedule.schedule_type)
                printl("  Schedule name", room.schedule.name)
                printl("  Schedule target temp", room.schedule.current_target_temperature)
                printl("  Schedule next setting time", room.schedule.next_entry.time)

            # Use first room for controls tests
            room_name = wh.get_room_by_id(1).name
            printl("Control test room (room id 1)", room_name)

            
            room = wh.get_room_by_name(room_name)
            
            printl("  Set window detection", "")
            room.window_detection_active = room.window_detection_active
            mode = room.mode
            printl("  Set mode auto", "")
            room.mode = WiserModeEnum.auto
            printl("  Set mode manual", "")
            room.mode = WiserModeEnum.manual
            printl("  Set mode off", "")
            room.mode = WiserModeEnum.off
            printl("  Set room name", "")
            room.name = room.name
            printl("  Set boost", room.set_boost(1, 60))
            printl("  Cancel boost", room.cancel_boost())
            printl("  Set room temp", room.override_temperature(20))
            printl(
                "  Set room temp for 60 mins", room.override_temperature_for_duration(23, 90)
            )
            printl("  Schedule advance", room.schedule_advance())
            printl("  Cancel all overrides", room.cancel_overrides())
            

            # Set room back to auto
            printl("  Set mode back to original state", mode.value)
            room.mode = mode
  
            success("Rooms data and controls test successful")

    # ----------------------------------
    # Schedules
    # ----------------------------------
    if TEST_SCHEDULES:
        test_start("Schedule data and controls")
        if len(wh.schedules) == 0:
            fail("No schedules found on hub")
        else:
            for schedule in wh.schedules:
                printl("Schedule type", schedule.schedule_type)
                printl("Schedule id", schedule.id)
                printl("Schedule name", schedule.name)
                printl("Schedule next event", schedule.next_entry.time)
                printl("Next schedule entry", schedule.next_entry.setting)
                if schedule.schedule_type == "Heating":
                    printl(
                        "Schedule current target temp", schedule.current_target_temperature
                    )
                else:
                    printl("Schedule current state", schedule.current_state)

            # Control tests
            printl(
                "Saving json schedule to file - schedule.json",
                schedule.save_schedule_to_file("schedule.json"),
            )
            printl(
                "Saving yaml schedule to file - schedule.yaml",
                schedule.save_schedule_to_yaml_file("schedule.yaml"),
            )
            printl(
                "Set schedule from data", schedule.set_schedule(schedule.schedule_data)
            )
            printl(
                "Set schedule from json file",
                schedule.set_schedule_from_file("schedule.json"),
            )
            printl(
                "Set schedule from yaml file",
                schedule.set_schedule_from_yaml_file("schedule.yaml"),
            )

            # Test schedule copy if more than 1 room exists
            if len(wh.rooms) >= 2:
                # Keep room2 schedule data to put back
                rm2schedule = wh.rooms[1].schedule.schedule_data

                printl(
                    "Copying " + wh.rooms[0].name + " schedule to " + wh.rooms[1].name,
                    wh.rooms[0].schedule.copy_schedule(wh.rooms[1].schedule.id),
                )
                printl(
                    "Reset " + wh.rooms[1].name + " to previous schedule",
                    wh.rooms[1].schedule.set_schedule(rm2schedule),
                )

            success("Schedule data and controls test successful")

    # ----------------------------------
    # Devices
    # ----------------------------------
    if TEST_DEVICES:
        test_start("Device data and controls")
        if len(wh.devices) == 0:
            fail("No devices (smart valves, smart plugs or room stats) found on hub")
        else:
            for device in wh.devices:
                print("---------------------")
                printl("Device id", device.id)
                printl("Device type", device.product_type)
                print("---------------------")
                printl("Device node id", device.node_id)
                printl("Device model", device.model)
                printl("Device firmware version", device.firmware_version)
                printl("Device serial no", device.serial_number)
                printl("Device parent node id", device.parent_node_id)
                printl(
                    "Device parent node type",
                    wh.get_device_by_node_id(device.parent_node_id).product_type,
                )
                # If parent device is not controller then get name of parent device
                if device.parent_node_id != 0:
                    printl(
                        "Device parent name",
                        wh.get_smart_plug_by_id(
                            wh.get_device_by_node_id(device.parent_node_id).id
                        ).name,
                    )
                else:
                    printl(
                        "Device parent name",
                        wh.get_device_by_node_id(device.parent_node_id).product_type,
                    )
                printl("Device RSSI", device.signal.rssi)

                printl(
                    "Device signal strength",
                    str(device.signal.signal_strength) + "%",
                )
                printl(
                    "Device signal strength description",
                    device.signal.displayed_signal_strength,
                )

                if device.product_type == "iTRV":
                    sv = wh.get_smart_valve_by_id(device.id)
                    printl("Device battery percent", sv.battery.percent)
                    printl("Device battery level", sv.battery.level)
                    printl("Device battery voltage", sv.battery.voltage)
                    printl("Device target temp", sv.current_target_temperature)
                    printl("Device current temp", sv.current_temperature)
                    printl("Device lock enabled", sv.device_lock_enabled)
                    printl("Device orientation", sv.mounting_orientation)
                    printl("Device percentage demand", sv.percentage_demand)
                    
                    # Commands
                    printl("Set device lock to false", "")
                    sv._device_lock_enabled = False
                    printl("Set indentify to false","")
                    sv.identify = False
                    
                if device.product_type == "RoomStat":
                    rs = wh.get_room_stat_by_id(device.id)
                    printl("Device battery percent", rs.battery.percent)
                    printl("Device battery level", rs.battery.level)
                    printl("Device battery voltage", rs.battery.voltage)
                    printl("Device target temp", rs.current_target_temperature)
                    printl("Device current temp", rs.current_temperature)
                    printl("Device current humidity", rs.current_humidity)
                    printl("Device lock enabled", rs.device_lock_enabled)
                    
                    # Commands
                    printl("Set device lock to false", "")
                    rs.device_lock_enabled = False
                    printl("Set indentify to false","")
                    rs.identify = False

                if device.product_type == "SmartPlug":
                    sp = wh.get_smart_plug_by_id(device.id)
                    printl("Device away action", sp.away_action)
                    printl("Device control source", sp.control_source)
                    printl("Device is on", sp.is_on)
                    printl("Device manual state", sp.manual_state)
                    printl("Device mode", sp.mode)
                    printl("Device name", sp.name)
                    printl("Device room id", sp.room_id)
                    printl("Device schedule state", sp.scheduled_state)
                    printl("Device schedule next event time", sp.schedule.next_entry.time)
                    # Commands
                    printl("Set device mode to auto", "")
                    #sp.mode = WiserModeEnum.auto
                    printl("Set device mode to manual", "")
                    #sp.mode = WiserModeEnum.manual
                    printl("Turn device on", "")
                    #sp.turn_on()
                    printl("Turn device off", "")
                    #sp.turn_off()
                    printl("Set away action to no change", "")
                    #sp.away_action = WiserAwayActionEnum.no_change
                print("")

            success("Device data and controls test successful")

    # ----------------------------------
    # Hot Water
    # ----------------------------------
    if TEST_HOTWATER:
        test_start("Hot Water data and controls")
        if wh.hotwater is None:
            fail("Hot water not supported on this hub")
        else:
            hw = wh.hotwater
            printl("Hot water current control source", hw.current_control_source)
            printl("Hot water id", hw.id)
            #printl("Hot water ignore away mode", hw.ignoreAwayMode)
            printl("Hot water is heating", hw.is_heating)
            printl("Hot water is boosted", hw.is_boosted)
            printl("Hot water mode", hw.mode)
            printl("Hot water schedule next event time", hw.schedule.next_entry.time)
            """
            # Commands
            printl("Turn hot water on", hw.turnOn())
            printl("Turn hot water off", hw.turnOff())
            printl("Set hot water mode to manual", hw.setModeManual())
            printl("Set hot water mode to auto", hw.setModeAuto)
            printl("Set on override for 10 mins", hw.setOverrideOn(10))
            printl("Set off override for 30 mins", hw.setOverrideOff(30))
            printl("Cancel overrides", hw.cancelOverride())
            """
            success("Hot water data and controls testing successful")
    # ----------------------------------
    # Heating Channel
    # ----------------------------------
    if TEST_HEATING:
        test_start("Heating channel data")
        if len(wh.heating) < 1:
            fail("No heating device found on hub")
        else:
            for hc in wh.heating:
                printl("Heating channel id", hc.id)
                printl("Heating channel name", hc.name)
                printl("Heating channel room ids", hc.room_ids)
                for room in hc.rooms:
                    printl("Room name:", room.name)
                printl("Percentage demand", hc.percentage_demand)
                printl("Demand on/off output", hc.demand_on_off_output)
                printl("Heating relay state", hc.heating_relay_status)
                printl(
                    "Is smart valve preventing demand?", hc.is_smart_valve_preventing_demand
                )
            success("Heating channel data testing successful")

    # ----------------------------------
    # Test Data Refresh
    # ----------------------------------
    if TEST_REFRESH:
        test_start("Refresh data")
        for i in range(1):
            print(h.heap())
            printl("Read hub data", wh.read_hub_data())
            print(h.heap().byrcs[1].byid)
            # Iterate through wiser entity objects
            # Main data stores
            if not wh._domain_data:
                raise Exception("No data in domainData")
            else:
                printl("Domain data", "Success")

            if not wh._network_data:
                raise Exception("No data in networkData")
            else:
                printl("Network data", "Success")

            if not wh._schedule_data:
                raise Exception("No data in scheduleData")
            else:
                printl("Schedule data", "Success")

            printl("# Rooms", len(wh.rooms))
            time.sleep(3)


except WiserHubConnectionError as ex:
    fail(ex.args[0])

except WiserHubAuthenticationError as ex:
    fail(ex.args[0])

except WiserHubRESTError as ex:
    fail(ex.args[0])

except Exception as ex:
    fail("Exception error during tests")
    raise

# Summary
if error_count > 0:
    print("Tests completed with {} values not found on the hub.  This may not be a problem".format(error_count))
else:
    print("Tests completed with no errors")
