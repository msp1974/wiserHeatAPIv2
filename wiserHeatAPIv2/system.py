from . import _LOGGER

from .device import _WiserSignalStrength
from .helpers import (
    _WiserTemperatureFunctions as tf,
    _WiserCloud,
    _WiserFirmareUpgradeInfo,
    _WiserGPS,
    _WiserHubCapabilitiesInfo,
    _WiserNetwork,
    _WiserSignalStrength,
    _WiserZigbee
)
from .rest_controller import _WiserRestController

from .const import (
    TEXT_ON,
    TEXT_UNKNOWN,
    MAX_BOOST_INCREASE,
    WISERSYSTEM
)

from datetime import datetime
import inspect

class _WiserSystem(object):
    """Class representing a Wiser Hub device"""

    def __init__(
        self, 
        wiser_rest_controller: _WiserRestController, 
        domain_data: dict, 
        network_data: dict,
        device_data: dict
    ):

        self._wiser_rest_controller = wiser_rest_controller
        self._data = domain_data
        self._system_data = domain_data.get("System",{})

        # Sub classes for system setting values
        self._capability_data = _WiserHubCapabilitiesInfo(self._data.get("DeviceCapabilityMatrix",{}))
        self._cloud_data = _WiserCloud(self._system_data.get("CloudConnectionStatus"), self._data.get("Cloud",{}))
        self._device_data = self._get_system_device(device_data)
        self._network_data = _WiserNetwork(network_data.get("Station", {}))
        self._signal = _WiserSignalStrength(self._device_data)
        self._system_data = self._data.get("System",{})
        self._upgrade_data = _WiserFirmareUpgradeInfo(self._data.get("UpgradeInfo",{}))
        self._zigbee_data = _WiserZigbee( self._data.get("Zigbee",{}))

        # Variables to hold values for settabel values
        self._automatic_daylight_saving = self._system_data.get("AutomaticDaylightSaving")
        self._away_mode_affects_hotwater = self._system_data.get("AwayModeAffectsHotWater")
        self._away_mode_target_temperature = self._system_data.get("AwayModeSetPointLimit")
        self._comfort_mode_enabled = self._system_data.get("ComfortModeEnabled")
        self._degraded_mode_target_temperature = self._system_data.get(
            "DegradedModeSetpointThreshold"
        )
        self._eco_mode_enabled = self._system_data.get("EcoModeEnabled")
        self._hub_time = datetime.fromtimestamp(self._system_data.get("UnixTime"))
        self._override_type = self._system_data.get("OverrideType", "")
        self._timezone_offset = self._system_data.get("TimeZoneOffset")
        self._valve_protection_enabled = self._system_data.get("ValveProtectionEnabled")

    def _get_system_device(self, device_data: dict):
        for device in device_data:
                # Add controller to sytem class
                if device.get("ProductType") == "Controller":
                    return device

    def _send_command(self, cmd: dict) -> bool:
        """
        Send system control command to Wiser Hub
        param cmd: json command structure
        return: boolen - true = success, false = failed
        """
        result = self._wiser_rest_controller._send_command(WISERSYSTEM, cmd)
        if result:
            _LOGGER.debug(
                "Wiser hub - {} command successful".format(inspect.stack()[1].function)
            )
        return result
    

    @property
    def active_system_version(self) -> str:
        """Get current hub firmware version"""
        return self._system_data.get("ActiveSystemVersion", TEXT_UNKNOWN)

    @property
    def automatic_daylight_saving_enabled(self) -> bool:
        """Get or set if auto daylight saving is enabled"""
        return self._automatic_daylight_saving

    @automatic_daylight_saving_enabled.setter
    def automatic_daylight_saving_enabled(self, enabled: bool):
        if self._send_command({"AutomaticDaylightSaving": str(enabled).lower()}):
            self._automatic_daylight_saving = enabled

    @property
    def away_mode_enabled(self) -> bool:
        """Get or set if away mode is enabled"""
        return True if self._override_type == "Away" else False

    @away_mode_enabled.setter
    def away_mode_enabled(self, enabled: bool):
        if self._send_command({"RequestOverride": {"Type": 2 if enabled else 0}}):
            self._override_type = "Away" if enabled else ""

    @property
    def away_mode_affects_hotwater(self) -> bool:
        """Get or set if setting away mode affects hot water"""
        return self._away_mode_affects_hotwater

    @away_mode_affects_hotwater.setter
    def away_mode_affects_hotwater(self, enabled: bool = False):
        if self._send_command({"AwayModeAffectsHotWater": str(enabled).lower()}):
            self._away_mode_affects_hotwater = enabled

    @property
    def away_mode_target_temperature(self) -> float:
        """Get or set target temperature for away mode"""
        return tf._from_wiser_temp(self._away_mode_target_temperature)

    @away_mode_target_temperature.setter
    def away_mode_target_temperature(self, temp: float):
        temp = tf._to_wiser_temp(temp)
        if self._send_command({"AwayModeSetPointLimit": temp}):
            self._away_mode_target_temperature = tf._to_wiser_temp(temp)

    @property
    def boiler_fuel_type(self) -> str:
        """Get boiler fuel type setting"""
        # TODO: Add ability to set to 1 of 3 types
        return self._system_data.get("BoilerSettings", {"FuelType": TEXT_UNKNOWN}).get(
            "FuelType"
        )

    @property
    def brand_name(self) -> str:
        """Get brand name of Wiser hub"""
        return self._system_data.get("BrandName")

    @property
    def capabilities(self) -> _WiserHubCapabilitiesInfo:
        """Get capability info"""
        return self._capability_data

    @property
    def cloud(self) -> _WiserCloud:
        """Get cloud settings"""
        return self._cloud_data

    @property
    def comfort_mode_enabled(self) -> bool:
        """Get or set if comfort mode is enabled"""
        return self._comfort_mode_enabled

    @comfort_mode_enabled.setter
    def comfort_mode_enabled(self, enabled: bool):
        if self._send_command({"ComfortModeEnabled": enabled}):
            self._comfort_mode_enabled = enabled

    @property
    def degraded_mode_target_temperature(self) -> float:
        """Get or set degraded mode target temperature"""
        return tf._from_wiser_temp(self._degraded_mode_target_temperature)

    @degraded_mode_target_temperature.setter
    def degraded_mode_target_temperature(self, temp: float):
        temp = temp._to_wiser_temp(temp)
        if self._send_command({"DegradedModeSetpointThreshold": temp}):
            self._degraded_mode_target_temperature = temp

    @property
    def eco_mode_enabled(self) -> bool:
        """Get or set whether eco mode is enabled"""
        return self._eco_mode_enabled

    @eco_mode_enabled.setter
    def eco_mode_enabled(self, enabled: bool):
        if self._send_command({"EcoModeEnabled": enabled}):
            self._eco_mode_enabled = enabled

    @property
    def firmware_over_the_air_enabled(self) -> bool:
        """Whether firmware updates over the air are enabled on the hub"""
        return self._system_data.get("FotaEnabled")

    @property
    def firmware_version(self) -> str:
        """Get firmware version of device"""
        return self._device_data.get("ActiveFirmwareVersion", TEXT_UNKNOWN)

    @property
    def geo_position(self) -> _WiserGPS:
        """Get geo location information"""
        return _WiserGPS(self._system_data.get("GeoPosition", {}))

    @property
    def hardware_generation(self) -> int:
        """Get hardware generation version"""
        return self._system_data.get("HardwareGeneration", 0)

    @property
    def heating_button_override_state(self) -> bool:
        """Get if heating override button is on"""
        return (
            True if self._system_data.get("HeatingButtonOverrideState") == TEXT_ON else False
        )

    @property
    def hotwater_button_override_state(self) -> bool:
        """Get if hot water override button is on"""
        return (
            True if self._system_data.get("HotWaterButtonOverrideState") == TEXT_ON else False
        )

    @property
    def hub_time(self) -> datetime:
        """Get the current time on hub"""
        return self._hub_time

    @property
    def id(self) -> int:
        """Get id of device"""
        return self._device_data.get("id")

    @property
    def is_away_mode_enabled(self) -> bool:
        """Get if away mode is enabled"""
        return True if self._override_type == "Away" else False

    @property
    def model(self) -> str:
        """Get model of device"""
        return self._device_data.get("ModelIdentifier", TEXT_UNKNOWN)

    @property
    def name(self) -> str:
        """Get name of hub"""
        return self.network.hostname

    @property
    def network(self) -> _WiserNetwork:
        """Get network information from hub"""
        return self._network_data

    @property
    def node_id(self) -> int:
        """Get zigbee node id of device"""
        return self._device_data.get("NodeId", 0)

    @property
    def opentherm_connection_status(self) -> str:
        """Get opentherm connection status"""
        return self._system_data.get("OpenThermConnectionStatus", TEXT_UNKNOWN)

    @property
    def pairing_status(self) -> str:
        """Get account pairing status"""
        return self._system_data.get("PairingStatus", TEXT_UNKNOWN)
    
    @property
    def parent_node_id(self) -> int:
        """Get zigbee node id of device this device is connected to"""
        return self._device_data.get("ParentNodeId", 0)

    @property
    def product_type(self) -> str:
        """Get product type of device"""
        return self._device_data.get("ProductType", TEXT_UNKNOWN)

    @property
    def signal(self) -> _WiserSignalStrength:
        """Get zwave network information"""
        return self._signal

    @property
    def system_mode(self) -> str:
        """Get current system mode"""
        return self._system_data.get("SystemMode", TEXT_UNKNOWN)

    @property
    def timezone_offset(self) -> int:
        """Get timezone offset in minutes"""
        return self._timezone_offset

    @timezone_offset.setter
    def timezone_offset(self, offset: int):
        if self._send_command({"TimeZoneOffset": offset}):
            self._timezone_offset = offset

    @property
    def user_overrides_active(self) -> bool:
        """Get if any overrides are active"""
        return self._system_data.get("UserOverridesActive", False)

    @property
    def valve_protection_enabled(self) -> bool:
        """Get or set if valve protection is enabled"""
        return self._valve_protection_enabled

    @valve_protection_enabled.setter
    def valve_protection_enabled(self, enabled: bool):
        """
        Set the valve protection setting on the wiser hub
        param enabled: turn on or off
        """
        if self._send_command({"ValveProtectionEnabled": enabled}):
            self._valve_protection_enabled = enabled

    @property
    def zigbee(self) -> _WiserZigbee:
        """Get zigbee info"""
        return self._zigbee_data


    def boost_all_rooms(self, inc_temp: float, duration: int) -> bool:
        """
        Boost the temperature of all rooms
        param inc_temp: increase target temperature over current temperature by 0C to 5C
        param duration: the duration to boost the room temperatures in minutes
        return: boolean
        """
        return self._send_command(
            {
                "RequestOverride": {
                    "Type": "Boost",
                    "DurationMinutes": duration,
                    "IncreaseSetPointBy": tf._to_wiser_temp(inc_temp, "delta")
                }
            }
        )

    def cancel_all_overrides(self):
        """
        Cancel all overrides and set room schedule to the current temperature setting for the mode
        return: boolean
        """
        return self._send_command({"RequestOverride": {"Type": "CancelUserOverrides"}})


