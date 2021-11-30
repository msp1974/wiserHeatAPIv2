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
TRV_MIN_BATTERY_LEVEL = 2.5

# Other Constants
REST_TIMEOUT = 15


# Text Values
TEXT_AUTO = "Auto"
TEXT_DEGREESC = "DegreesC"
TEXT_HEATING = "Heating"
TEXT_MANUAL = "Manual"
TEXT_NO_CHANGE = "NoChange"
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
WISERDEVICE = "Device/{}"
WISERHOTWATER = "HotWater/{}"
WISERROOM = "Room/{}"
WISERSMARTVALVE = "SmartValve/{}"
WISERROOMSTAT = "RoomStat/{}"
WISERSMARTPLUG = "SmartPlug/{}"

# Enums
class WiserUnitsEnum(enum.Enum):
    imperial = "imperial"
    metric = "metric"
