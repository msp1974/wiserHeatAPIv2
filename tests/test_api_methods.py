from params import HOST, KEY

import pathlib
import sys
import time

sys.path.append(pathlib.Path(__file__).parent.resolve())

from wiserHeatAPIv2.const import TEXT_UNKNOWN
from wiserHeatAPIv2 import wiserhub

BOOL = [True, False]
LEVELCOLOURS = ["\033[95m","\033[94m","\033[96m","\033[92m"]


class bcolors:
    HEADER = "\033[94m"
    LINK = "\033[95m"
    NORMAL = "\033[97m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"

def fn(h: object, fn_name: str, args: dict = {}):
    output = ""

    print(f"Calling function {fn_name} with parameters {args}")

    try:
        fn = getattr(h, fn_name)
        result = fn(**args)
        if result:
            if type(result) != bool:
                print(f"Result: {result.name}")
            print(f"{bcolors.OKGREEN}Passed{bcolors.NORMAL}")
        else:
            print(f"{bcolors.WARNING} ERROR - {result}{bcolors.NORMAL}")
    except Exception as ex:
        print(f"{bcolors.FAIL}ERROR - {ex}{bcolors.NORMAL}")
        raise ex

 
def test_methods(h: wiserhub.WiserAPI):

    # Room - just pick first one
    if h.rooms.count > 0:
        # Room collection methods
        room = h.rooms.all[0]

        fn(h.rooms, "get_by_id", {"id": room.id})
        fn(h.rooms, "get_by_name", {"name": room.name})
        fn(h.rooms, "get_by_schedule_id", {"schedule_id": room.schedule.id})
        fn(h.rooms, "get_by_device_id", {"device_id": room.devices[0].id})

        fn(room, "boost", {"inc_temp":2, "duration":5})
        fn(room, "cancel_boost", {})
        fn(room, "set_target_temperature", {"temp":18})
        fn(room, "set_target_temperature_for_duration", {"temp":17, "duration":5})
        fn(room, "set_manual_temperature", {"temp":16})
        fn(room, "schedule_advance", {})
        fn(room, "cancel_overrides", {})

        
        # Schedules
        fn(room.schedule, "set_schedule", {"schedule_data": room.schedule.schedule_data})

        fn(room.schedule, "save_schedule_to_file", {"schedule_file": "test_json_schedule.json"})
        fn(room.schedule, "set_schedule_from_file", {"schedule_file": "test_json_schedule.json"})

        fn(room.schedule, "save_schedule_to_yaml_file", {"schedule_yaml_file": "test_json_schedule.yaml"})
        fn(room.schedule, "set_schedule_from_yaml_file", {"schedule_yaml_file": "test_json_schedule.yaml"})

        # Test copy schedule between rooms - need at least 2 rooms
        if h.rooms.count >= 2:
            # Save current room schedule
            rm = h.rooms.all[1]
            rm_sched = rm.schedule.schedule_data
            fn(room.schedule, "copy_schedule", {"to_id": rm.schedule.id})
            #Set it back to original
            fn(rm.schedule, "set_schedule", {"schedule_data": rm_sched})

    else:
        print(f"{bcolors.OKBLUE}No rooms in system to test{bcolors.NORMAL}")

    
    # Test Hotwater
    if h.hotwater:
        fn(h.hotwater, "schedule_advance", {})
        fn(h.hotwater, "boost", {"duration": 10})
        fn(h.hotwater, "override_state", {"state":"on"})
        fn(h.hotwater, "override_state_for_duration", {"duration":5, "state":"off"})
        fn(h.hotwater, "cancel_overrides", {})
    else:
        print(f"{bcolors.OKBLUE}No hot water in system to test{bcolors.NORMAL}")


    # System
    fn(h.system, "boost_all_rooms", {"inc_temp":2, "duration":5})
    fn(h.system, "cancel_all_overrides", {})


def test_system():
    print("**********************************************************")
    print ("Testing WiserHub API Methods")
    print("**********************************************************")
    try:
        h = wiserhub.WiserAPI(HOST, KEY)
        test_methods(h)
    except Exception as ex:
        print (f"Error: {ex}")

test_system()