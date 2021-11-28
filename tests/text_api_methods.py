from params import HOST, KEY

import sys

from wiserHeatAPIv2.const import TEXT_UNKNOWN
sys.path.append('/home/mark/development/wiserHeatAPIv2/')
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
            print(f"{bcolors.OKGREEN}Passed{bcolors.NORMAL}")
        else:
            print(f"{bcolors.WARNING} ERROR - {result}{bcolors.NORMAL}")
    except Exception as ex:
        print(f"{bcolors.FAIL}ERROR - {ex}{bcolors.NORMAL}")

 
def test_methods(h: wiserhub.WiserAPI):
       
    # Room - just pick first one
    if h.rooms.count > 0:
        fn(h.rooms.all[0], "boost", {"inc_temp":2, "duration":5})
        fn(h.rooms.all[0], "cancel_boost", {})
        fn(h.rooms.all[0], "set_target_temperature", {"temp":18})
        fn(h.rooms.all[0], "set_target_temperature_for_duration", {"temp":17, "duration":5})
        fn(h.rooms.all[0], "set_manual_temperature", {"temp":16})
        fn(h.rooms.all[0], "schedule_advance", {})
        fn(h.rooms.all[0], "cancel_overrides", {})
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
    h = wiserhub.WiserAPI(HOST, KEY)
    test_methods(h)

test_system()