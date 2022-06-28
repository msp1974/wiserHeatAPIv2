import enum

# Temperature Constants
DEFAULT_AWAY_MODE_TEMP = 10.5
DEFAULT_DEGRADED_TEMP = 18
MAX_BOOST_INCREASE = 5
TEMP_ERROR = 2000
TEMP_MINIMUM = 5
TEMP_MAXIMUM = 30
TEMP_HW_ON = 110
TEMP_HW_OFF = -20
TEMP_OFF = -20

# Battery Constants
ROOMSTAT_MIN_BATTERY_LEVEL = 1.7
ROOMSTAT_FULL_BATTERY_LEVEL = 2.7
TRV_FULL_BATTERY_LEVEL = 3.0
TRV_MIN_BATTERY_LEVEL = 2.4

# Other Constants
REST_BACKOFF_FACTOR = 1
REST_RETRIES = 3
REST_TIMEOUT = 5

# Text Values
TEXT_AUTO = "Auto"
TEXT_CLOSE = "Close"
TEXT_DEGREESC = "DegreesC"
TEXT_HEATING = "Heating"
TEXT_LEVEL = "Level"
TEXT_LIGHTING = "Lighting"
TEXT_MANUAL = "Manual"
TEXT_NO_CHANGE = "NoChange"
TEXT_OFF = "Off"
TEXT_ON = "On"
TEXT_ONOFF = "OnOff"
TEXT_OPEN = "Open"
TEXT_SETPOINT = "Setpoint"
TEXT_SHUTTERS = "Shutters"
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
SPECIAL_TIMES = {"Sunrise":3000, "Sunset": 4000}

# Battery Level Enum
TRV_BATTERY_LEVEL_MAPPING = { 3.0:100, 2.9:80, 2.8:60, 2.7:40, 2.6:30, 2.5:20, 2.4:10, 2.3:0 }

# Wiser Hub Rest Api URL Constants
WISERHUBURL = "http://{}/data/v2/"
WISERHUBDOMAIN = WISERHUBURL + "domain/"
WISERHUBNETWORK = WISERHUBURL + "network/"
WISERHUBSCHEDULES = WISERHUBURL + "schedules/"
WISERHUBOPENTHERM = WISERHUBURL + "opentherm/"
WISERSYSTEM = "System"
WISERDEVICE = "Device/{}"
WISERHOTWATER = "HotWater/{}"
WISERROOM = "Room/{}"
WISERSMARTVALVE = "SmartValve/{}"
WISERROOMSTAT = "RoomStat/{}"
WISERSMARTPLUG = "SmartPlug/{}"
WISERHEATINGACTUATOR = "HeatingActuator/{}"
WISERUFHCONTROLLER = "UnderFloorHeating/{}"
WISERSHUTTER = "Shutter/{}"
WISERLIGHT = "Light/{}"

# Enums
class WiserUnitsEnum(enum.Enum):
    imperial = "imperial"
    metric = "metric"

DEFAULT_LEVEL_SCHEDULE = {
    "Monday": {"Time":[],"Level":[]},
    "Tuesday": {"Time":[],"Level":[]},
    "Wednesday": {"Time":[],"Level":[]},
    "Thursday": {"Time":[],"Level":[]},
    "Friday": {"Time":[],"Level":[]},
    "Saturday": {"Time":[],"Level":[]},
    "Sunday": {"Time":[],"Level":[]}
}
