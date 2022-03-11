#!/usr/bin/env python3
"""
# Wiser API Version 2

Tested in WiserHub version 3.8.8

angelosantagata@gmail.com
msparker@sky.com


https://github.com/asantaga/wiserheatingapi


This API allows you to get information from and control your wiserhub.
"""

# TODO: Keep objects and update instead of recreating on hub update
# TODO: Update entity values after commend issued to get current values
import pathlib
from . import _LOGGER, __VERSION__

from .const import (
    DEFAULT_AWAY_MODE_TEMP,
    DEFAULT_DEGRADED_TEMP,
    MAX_BOOST_INCREASE,
    TEMP_ERROR,
    TEMP_HW_ON,
    TEMP_HW_OFF,
    TEMP_MINIMUM,
    TEMP_MAXIMUM,
    TEMP_OFF,
    WiserUnitsEnum,
    WISERHUBDOMAIN,
    WISERHUBNETWORK,
    WISERHUBSCHEDULES
)

from .exceptions import (
    WiserHubConnectionError,
    WiserHubAuthenticationError,
    WiserHubRESTError,
)

from .cli import log_response_to_file
from .devices import _WiserDeviceCollection
from .heating import _WiserHeatingChannelCollection
from .hot_water import _WiserHotwater
from .moments import _WiserMomentCollection
from .rest_controller import _WiserRestController, _WiserConnection
from .room import _WiserRoomCollection
from .schedule import _WiserScheduleCollection, WiserScheduleTypeEnum
from .system import _WiserSystem


class WiserAPI(object):
    """
    Main api class to access all entities and attributes of wiser system
    """
    def __init__(self, host: str, secret: str, units: WiserUnitsEnum = WiserUnitsEnum.metric):
        
        # Connection variables
        self._wiser_api_connection = _WiserConnection()
        self._wiser_rest_controller = None

        #Set connection params
        self._wiser_api_connection.host = host
        self._wiser_api_connection.secret = secret
        self._wiser_api_connection.units = units

        # Data stores for exposed properties
        self._devices = None
        self._hotwater = None
        self._heating_channels = None
        self._moments = None
        self._rooms = None
        self._schedules = None
        self._system = None

        # Log initialisation info
        _LOGGER.info(f"WiserHub API v{__VERSION__} Initialised - Host: {host}, Units: {self._wiser_api_connection.units.name.title()}")

        # Read hub data if hub IP and secret exist
        if (
            self._wiser_api_connection.host is not None
            and self._wiser_api_connection.secret is not None
        ):
            self.read_hub_data()
        else:
            raise WiserHubConnectionError("Missing or incomplete connection information")


    def read_hub_data(self):
        """Read all data from hub and populate objects"""
        # Create an instance of the rest controller
        self._wiser_rest_controller = _WiserRestController(self._wiser_api_connection)

        # Read data from hub
        _domain_data = self._wiser_rest_controller._get_hub_data(WISERHUBDOMAIN)
        _network_data = self._wiser_rest_controller._get_hub_data(WISERHUBNETWORK)
        _schedule_data = self._wiser_rest_controller._get_hub_data(WISERHUBSCHEDULES)

        if _domain_data != {} and _network_data != {} and _schedule_data != {}:

            # Schedules Collection
            self._schedules = _WiserScheduleCollection(self._wiser_rest_controller, _schedule_data)

            # System Object
            _device_data = _domain_data.get("Device", [])
            self._system = _WiserSystem(self._wiser_rest_controller, _domain_data, _network_data, _device_data)

            # Devices Collection
            self._devices = _WiserDeviceCollection(self._wiser_rest_controller, _domain_data, self._schedules )

            # Rooms Collection
            room_data = _domain_data.get("Room", [])
            self._rooms = _WiserRoomCollection(self._wiser_rest_controller, room_data, self._schedules.get_by_type(WiserScheduleTypeEnum.heating), self._devices)

            # Hot Water
            if _domain_data.get("HotWater"):
                schedule = self._schedules.get_by_id(WiserScheduleTypeEnum.onoff, _domain_data.get("HotWater")[0].get("ScheduleId", 0))
                self._hotwater = _WiserHotwater(
                    self._wiser_rest_controller,
                    _domain_data.get("HotWater", {})[0],
                    schedule,
                )

            # Heating Channels
            if _domain_data.get("HeatingChannel"):
                self._heating_channels = _WiserHeatingChannelCollection(
                    _domain_data.get("HeatingChannel"),
                    self._rooms
                )

            # Moments
            if _domain_data.get("Moment"):
                self._moments = _WiserMomentCollection(self._wiser_rest_controller, _domain_data.get("Moment"))

            # If gets here with no exceptions then success and return true
            return True

        return False
        

    # API properties
    @property
    def devices(self):
        """List of device entities attached to the Wiser Hub"""
        return self._devices

    @property
    def heating_channels(self):
        """List of heating channel entities on the Wiser Hub"""
        return self._heating_channels

    @property
    def hotwater(self):
        """List of hot water entities on the Wiser Hub"""
        return self._hotwater

    @property
    def moments(self):
        """List of moment entities on the Wiser Hub"""
        return self._moments

    @property
    def rooms(self):
        """List of room entities configured on the Wiser Hub"""
        return self._rooms

    @property
    def schedules(self):
        """List of schedules"""
        return self._schedules

    @property
    def system(self):
        """Entity of the Wiser Hub"""
        return self._system

    @property
    def units(self) -> WiserUnitsEnum:
        """Get or set units for temperature"""
        return self._wiser_api_connection.units

    @units.setter
    def units(self, units: WiserUnitsEnum):
        self._wiser_api_connection.units = units

    @property
    def version(self):
        return __VERSION__

    def output_raw_hub_data(self, data_class: str, filename: str, file_path: str) -> bool:
        """Output raw hub data to json file"""
        # Get correct endpoint
        if data_class.lower() == 'domain':
            endpoint = WISERHUBDOMAIN
        elif data_class.lower() == 'network':
            endpoint = WISERHUBNETWORK
        elif data_class == 'schedules':
            endpoint = WISERHUBSCHEDULES
        else:
            endpoint = None

        # Get raw json data
        if endpoint:
            data = self._wiser_rest_controller._get_hub_data(endpoint)
            try:
                if data:
                    # Write out to file
                    log_response_to_file(data, filename, False, pathlib.Path(file_path))
                    return True
            except Exception as ex:
                _LOGGER.error(ex)
                return False
