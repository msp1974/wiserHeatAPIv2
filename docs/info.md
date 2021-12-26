# Drayton Wiser HeatHub API Python Library


This library implements the local REST API for the Drayton Wiser Heathub System.  The following services are implemented:

- Hub Discovery
- Rooms
- iTRVs
- Heating Actuators (electric heating)
- Roomstats
- Smartplugs
- Hot Water
- System
- Shutters (basic)
- Lights (basic)

## Hub Discovery

The library allows discovery of Wiser Heathubs on your network using zeroconf mDns browsing.  The below code is an example of how to use:

```
from wiserHeatAPIv2.discovery import WiserDiscovery

try:
    w = WiserDiscovery()
    hubs = w.discover_hub()
    if hubs:
        for hub in hubs:
            print(f"Found hub {hub.name} with IP as {hub.ip} and Hostname as {hub.hostname}")

except Exception as ex:
    print(ex)
```

## Hub API

To create an instance of the hub and do and initial read of data form the HeatHub, see below example.

```
from wiserHeatAPIv2 import wiserhub
h = wiserhub.WiserAPI(HOST, KEY)
```

To update form the hub:

```
h.read_hub_data()
```

## Devices

The api holds a collection of all devices connected to your HeatHub.  See below for collections by device type. Collections are iterable ('all' property) and have methods to return a list of devices by criteria.  See the WiserDeviceCollection class in devices.py. They can be accessed as follows:

```
devices = h.devices.all
devices = h.devices.get_by_room_id(room_id)
devices = h.devices.get_by_room_name(room_name)
devices = h.devices.get_by_parent_node_id(node_id)

device = h.devices.get_by_id(id)
device = h.devices.get_by_node_id(node_id)
device = h.devices.get_by_serial_number(serial_no)

```
## SmartValve(iTRV), RoomStat, Heating Actuator and SmartPlug Devices
The api also provides collections of each device type connected to your HeatHub.  Collections are iterable ('all' property) and have methods to return a list of devices by criteria.  See the WiserSmartValveCollection, WiserRoomStatCollection and WiserSmartPlugCollection classes in smartvalve.py, roomstat.py and smartplug.py respectively.  The collections can be accessed as follows:

```
smartvalves = h.devices.smartvalves.all
smartvalve = h.devices.smartvalves.get_by_id(id)

roomstats = h.devices.roomstats.all
roomstat = h.devices.roomstats.get_by_id(id)

actuators = h.devices.heating_actuators.all
actuator = h.devices.heating_actuators.get_by_id(id)

smartplugs = h.devices.smartplugs.all
smartplug = h.devices.smartplugs.get_by_id(id)

shutters = h.devices.shutters.all
shutter = h.devices.shutters.get_by_id(id)

lights = h.devices.lights.all
light = h.devices.lights.get_by_id(id)
```

## Heating Channels
The api provides information on each heating channel on your HeatHub.  The varying models of HeatHub can provide 1 or 2 heating channels.  As such, this returns a collection.  See WiserHeatingCollection class in heating.py for methods to return a specific channel.  The collection can be accessed as follows:

```
heating_channels = h.heating_channels.all

heating_channel = h.heating_channels.get_by_id(id)
heating_channel = h.heating_channels.get_by_room_id(room_id)
heating_channel = h.heating_channels.get_by_room_name(room_name)
```

## Hot Water
If your hub supports hot water function, the api provides access to control this function.  See WiserHotWater class in hot_water.py for a full list of properties and methods.  The hot water object can be accessed as follows:

```
hotwater = h.hotwater
```

## Moments
The api provides the ability to activate Wiser Moments (scenes) set via the Wiser App.  It holds a collection of these.  See WiserMomentCollection in moments.py for a full list of properties and methods.  They can be accessed as follows:

```
moments = h.moments.all

moment = h.moments.get_by_id(id)

```

## Rooms
The api provides a collection of rooms on your Wiser HeatHub setup.  A room has a number of properties and methods that control the room temp setting etc and also links to devices in that room and the specific schedule for that room.  The collection is iterable ('all' property) and have methods to return a specific room by criteria.  See WiserRoom class in room.py for a list of properties and methods available.

```
rooms = h.rooms.all

room = h.room.get_by_id(id)
room = h.room.get_by_name(room_name)
room = h.room.get_by_device_id(device_id)
room = h.room.get_by_schedule_id(schedule_id)

```

## System

The system property allows control over the system wide settings on the hub.  It contains many properties and methods to control the hub.  See the WiserSystem class in system.py.  It can be accessed as:

```
system = h.system
```
&nbsp;


# Code Examples
The following are code examples to help you on your way to using this api.
```
from wiserHeatAPIv2 import wiserhub
h = wiserhub.WiserAPI(HOST, KEY)
```

### Devices (see device.py, smartvalve.py, roomstat.py, smartplugs.py)
```
# Get roomstat humidity
h.devices.roomstats.get_by_id(2).current_humidity

# Get device battery info
h.devices.smartvalves.get_by_id(1).battery.percent

# Make smartvalve identify itself (flash leds)
h.devices.smartvalves.get_by_id(1).identify = true
```


### Moments (see moments.py)
```
# Activate a Wiser Moment
h.moments.get_by_id(1).activate()
```

### Rooms (see room.py)
```
# Get current room temp
h.rooms.get_by_id(1).current_temperature

# Get room heating mode
h.rooms.get_by_id(1).mode

# Set room heating mode
h.rooms.get_by_id(1).mode = "Auto"

# Boost the room heating by 3C for 60mins
h.rooms.get_by_id(1).boost(3, 60)
```

### Room Schedules (see schedule.py)
```
# Get current schedule setting
h.rooms.get_by_id(1).schedule.current_setting

# Get schedule next setting
h.rooms.get_by_id(1).schedule.next.setting

# Set schedule from yaml file
h.rooms.get_by_id(1).schedule.set_schedule_from_file("schedule.yaml")
```

### System (see system.py and helpers.py)
```
# Set away mode
h.system.away_mode_enabled = true

# Get cloud connection status
h.system.cloud.connection_status

# Get hub Wifi signal strength
h.system.network.signal_percent

# Boost all rooms heating by 2C for 60 mins
h.system.boost_all_rooms(2, 60)

```