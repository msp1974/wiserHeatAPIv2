# Drayton Wiser Hub API v2 v0.0.26

This repository contains a simple API which queries the Drayton Wiser Heating sysystem used in the UK.

The API functionality provides the following functionality to control the wiser heating system for 1,2 and 3 channel heat hubs
The API also supports Smart Plugs and initial basic functionality for Shutter and Lights

## Installation



## 1. Find your HeatHub Secret key
Reference https://it.knightnet.org.uk/kb/nr-qa/drayton-wiser-heating-control/#controlling-the-system
1. Press the setup button on your HeatHub, the light will start flashing
Look for the Wi-Fi network (SSID) called **‘WiserHeatXXXXXX’** where XXXXXX is last 6 digits of the MAC address
2. Connect to the network from a Windows/Linux/Mac/Android/iPhone machine
3. Execute the secret url :-)
   * Open a browser to url `http://192.168.8.1/secret`
 
   This will return a string which is your system secret, store this somewhere. If you are running the test script simply put this value , with the ip address of the hub, in your wiserkeys.params

4. Press the setup button on the HeatHub again and it will go back to normal operations
5. Copy the secret and save it somewhere.
## 3. Find Your HEATHUB IP

Using your router, or something else, identify the IP address of your HeatHub, it usually identifies itself as the same ID as the ``WiserHeatXXXXXX`` 

Alternatively see the test_api_discovery.py file for how to use the api to discover your hub

## 4. Add values in you params.py to run tests
Create a file called params.py and place two lines, one with the wiser IP or hostname and the other with the secret key. 
e.g.
```
HOST=192.168.0.22
KEY=ABCDCDCDCCCDCDC

```

## 5. Run the sample
To help understand the api simply look at the test sample code ```tests/test_api_properties.py```, ```tests/test_api_methods.py``` or ```tests/test_api_discovery.py``` and the fully commented code. 

## 6. Documentation

Documentation available in [info.md](https://github.com/msp1974/wiserHeatAPIv2/blob/master/docs/info.md) in the docs directory and within comments in the code

*Changelog*

### 0.0.1
- Initial v2 release

### 0.0.2
- Updated setup.cfg

### 0.0.3
- Restructured code
- Added Wiser moments integration (minimal at present)

### 0.0.4
- Changed info logging to debug

### 0.0.7
- Fixed multiple bugs

### 0.0.8
- Fixed multiple bugs
- Added new features to work with HA integration

### 0.0.9
- Fixed moments bug not referencing rest controller
- Renamed smartplug away mode action
- Renamed smartplug power properties
- Cleaned up unnecessary code

### 0.0.10
- Added documentation on usage and examples [see info.md](https://github.com/msp1974/wiserHeatAPIv2/blob/master/docs/info.md)
- Discovery now returns class object
- Fix bug in away_mode_target_temperature setter

### 0.0.11
- Added number_of_smartvalves and smartvalve_ids properties

### 0.0.12
- Fix bug in boost_all_rooms that used incorrect temp delta

### 0.0.13
- Add support for Heating Actuator devices
- Add basic support for Shutters
- Add basic support for Lights

### 0.0.14
- Add room_id to all devices
- Add heating_actuator_ids, number_of_heating_actuators, device_lock properties to Heating Actuator devices
- Add additional overrides to _WiserElectricalDevice class
- Add signal_rssi_min and signal_rssi_max to network property

### 0.0.15
- Fix json error when hub returns control characters in string

### 0.0.16
- Added a cli interface to output json data from the hub for debugging

### 0.0.17
- Fixed path pointed to local dev machine instead of install dir for test scripts
- Fixed documentation link on Pypi
- Amended evaluation order for json sub branches in cli
- Added retries and backoff factor to improve hub connections on poor networks

### 0.0.20
- Fixed issue where setting mode to off when boosted did not cancel boost
- Bump ruamel.yaml to 0.17.20 to fix incompatibilitty issue with Python 3.10 - Issue [#2](https://github.com/msp1974/wiserHeatAPIv2/issues/2)
- Added version command to cli to output API version
- Added new properties to lights
- Added new properties to shutters
- Added new class for shutter lift range
- Added new method to write json output to file (output_raw_hub_data)
- Removed lift_open_time and lift_close_time and replace with _WiserLiftMovementRange class

### 0.0.23
- Added commands to control lights
- Added commands to control shutters
- Restructured schedules to manage heating, onoff and level types and their variation
- Reverted ruamel.yaml dependancy to 0.16.12 to resolve install issues on certain versions of Alpine linux

### 0.0.24
- Added initial support for UFH controller
- Fix to allow reported current temp below 5C

### 0.0.25
- Fix for schedule id returning None in light.py and shutter.py
- Rearchitected capabilities class
- Fix for command issue for current_lift in shutter.py
- Rename output_range to minimum and maximum from min/max in light.py
- Added product_identifier and product_model properties to devices
- Added manual_level, override_level and scheduled_percentage properties to light.py
- Added comfort_mode_score, control_direction, demand_type, displayed_setpoint and heating type properties to room.py
- Added version property to api
- Added available modes to lights and shutters collection
- Rearchitected how api holds and manages schedules
- Added schedule_id property to smartplugs and hot water

### 0.0.26
- Add onoff lights to light types

