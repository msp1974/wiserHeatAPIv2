# Drayton Wiser Hub API v2 v0.0.9

This repository contains a simple API which queries the Drayton Wiser Heating sysystem used in the UK.

The API functionality provides the following functionality to control the wiser heating system for 1,2 and 3 channel heat hubs

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

Alternatively see the wiserhub2apitest.py file for how to use the api to discover you hub

## 4. Add values in you wiserkeys.params
Create a file called wiserkeys.params and place two lines, one with the wiser IP and the other with the key it self. 
e.g.
```
wiserkey=ABCDCDCDCCCDCDC
wiserhubip=192.168.0.22
```

## 5. Run the sample
To help understand the api simply look at the sample code ```tests/test_api_properties.py``` and the fully commented code. 

## 6. Documentation

Documentation available in [docs](docs) directory and within comments in the code

*Changelog*

0.0.1
Initial v2 release

0.0.2
Updated setup.cfg

0.0.3
Restructured code
Added Wiser moments integration (minimal at present)

0.0.4
Changed info logging to debug

0.0.7
Fixed multiple bugs

0.0.8
Fixed multiple bugs
Added new features to work with HA integration