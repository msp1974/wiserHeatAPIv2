from . import _LOGGER

from .device import _WiserSignalStrength
from .helpers import _WiserTemperatureFunctions as tf
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
        temp = temp._to_wiser_temp(temp)
        if self._send_command({"AwayModeSetPointLimit": temp}):
            self._away_mode_target_temperature = temp._to_wiser_temp(temp)

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
    def capabilities(self) -> list:
        """Get capability info"""
        return self._capability_data

    @property
    def cloud(self):
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
    def geo_position(self):
        """Get geo location information"""
        return _WiserGPS(self._system_data.get("GeoPosition", {}))

    @property
    def hardware_generation(self):
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
    def network(self):
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

    #@property
    #def serial_number(self) -> str:
    #    """Get serial number of device"""
    #    return self._device_data.get("SerialNumber", TEXT_UNKNOWN)

    @property
    def signal(self) -> object:
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
    def zigbee(self):
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
                    "IncreaseSetPointBy": tf._to_wiser_temp(inc_temp)
                    if tf._to_wiser_temp(inc_temp) <= MAX_BOOST_INCREASE
                    else MAX_BOOST_INCREASE,
                }
            }
        )

    def cancel_all_overrides(self):
        """
        Cancel all overrides and set room schedule to the current temperature setting for the mode
        return: boolean
        """
        return self._send_command({"RequestOverride": {"Type": "CancelUserOverrides"}})


class _WiserNetwork:
    """Data structure for network information for a Wiser Hub"""

    def __init__(self, data: dict):
        self._data = data
        self._dhcp_status = data.get("DhcpStatus", {})
        self._network_interface = data.get("NetworkInterface", {})

    @property
    def dhcp_mode(self) -> str:
        """Get the current dhcp mode of the hub"""
        return self._data.get("NetworkInterface", {}).get("DhcpMode", TEXT_UNKNOWN)

    @property
    def hostname(self) -> str:
        """Get the host name of the hub"""
        return self._data.get("NetworkInterface", {}).get("HostName", TEXT_UNKNOWN)

    @property
    def ip_address(self) -> str:
        """Get the ip address of the hub"""
        if self.dhcp_mode == "Client":
            return self._dhcp_status.get("IPv4Address", TEXT_UNKNOWN)
        else:
            return self._network_interface.get("IPv4HostAddress", TEXT_UNKNOWN)

    @property
    def ip_subnet_mask(self) -> str:
        """Get the subnet mask of the hub"""
        if self.dhcp_mode == "Client":
            return self._dhcp_status.get("IPv4SubnetMask", TEXT_UNKNOWN)
        else:
            return self._network_interface.get("IPv4SubnetMask", TEXT_UNKNOWN)

    @property
    def ip_gateway(self) -> str:
        """Get the default gateway of the hub"""
        if self.dhcp_mode == "Client":
            return self._dhcp_status.get("IPv4DefaultGateway", TEXT_UNKNOWN)
        else:
            return self._network_interface.get("IPv4DefaultGateway", TEXT_UNKNOWN)

    @property
    def ip_primary_dns(self) -> str:
        """Get the primary dns server of the hub"""
        if self.dhcp_mode == "Client":
            return self._dhcp_status.get("IPv4PrimaryDNS", TEXT_UNKNOWN)
        else:
            return self._network_interface.get("IPv4PrimaryDNS", TEXT_UNKNOWN)

    @property
    def ip_secondary_dns(self) -> str:
        """Get the secondary dns server of the hub"""
        if self.dhcp_mode == "Client":
            return self._dhcp_status.get("IPv4SecondaryDNS", TEXT_UNKNOWN)
        else:
            return self._network_interface.get("IPv4SecondaryDNS", TEXT_UNKNOWN)

    @property
    def mac_address(self) -> str:
        """Get the mac address of the hub wifi interface"""
        return self._data.get("MacAddress", TEXT_UNKNOWN)

    @property
    def signal_percent(self) -> int:
        """Get the wifi signal strength percentage"""
        return min(100, int(2 * (self._data.get("RSSI", {}).get("Current", 0) + 100)))

    @property
    def signal_rssi(self) -> int:
        """Get the wifi signal rssi value"""
        return self._data.get("RSSI", {}).get("Current", 0)

    @property
    def security_mode(self) -> str:
        """Get the wifi security mode"""
        return self._data.get("SecurityMode", TEXT_UNKNOWN)

    @property
    def ssid(self) -> str:
        """Get the ssid of the wifi network the hub is connected to"""
        return self._data.get("SSID", TEXT_UNKNOWN)


class _WiserCloud:
    """Data structure for cloud information for a Wiser Hub"""

    def __init__(self, cloud_status: str, data: dict):
        self._cloud_status = cloud_status
        self._data = data

    @property
    def api_host(self) -> str:
        """Get the host name of the wiser cloud"""
        return self._data.get("WiserApiHost", TEXT_UNKNOWN)

    @property
    def bootstrap_api_host(self) -> str:
        """Get the bootstrap host name of the wiser cloud"""
        return self._data.get("BootStrapApiHost", TEXT_UNKNOWN)

    @property
    def connected_to_cloud(self) -> bool:
        """Get the hub connection status to the wiser cloud"""
        return True if self._cloud_status == "Connected" else False

    @property
    def connection_status(self) -> str:
        """Get the hub cloud connection status text"""
        return self._cloud_status

    @property
    def detailed_publishing_enabled(self) -> bool:
        """Get if detailed published is enabled"""
        return self._data.get("DetailedPublishing", False)

    @property
    def diagnostic_telemetry_enabled(self) -> bool:
        """Get if diagnostic telemetry is enabled"""
        return self._data.get("EnableDiagnosticTelemetry", False)


class _WiserZigbee:
    """Data structure for zigbee information for a Wiser Hub"""

    def __init__(self, data: dict):
        self._data = data

    @property
    def error_72_reset(self) -> int:
        """Get error72reset info"""
        return self._data.get("Error72Reset", 0)
    
    @property
    def jpan_count(self) -> int:
        """Get jpan count info"""
        return self._data.get("JPANCount", 0)

    @property
    def network_channel(self) -> int:
        """Get network channel info"""
        return self._data.get("NetworkChannel", 0)

    @property
    def no_signal_reset(self) -> int:
        """Get no signal reset info"""
        return self._data.get("NoSignalReset", 0)

    @property
    def module_version(self) -> str:
        """Get zigbee module version info"""
        return self._data.get("ZigbeeModuleVersion", TEXT_UNKNOWN)

    @property
    def eui(self) -> str:
        """Get zigbee eui info"""
        return self._data.get("ZigbeeEUI", TEXT_UNKNOWN)


class _WiserGPS:
    """Data structure for gps positional information for a Wiser Hub"""

    def __init__(self, data: dict):
        self._data = data

    @property
    def latitude(self) -> float:
        """Get the latitude of the hub"""
        return self._data.get("Latitude")

    @property
    def longitude(self) -> float:
        """Get the longitude of the hub"""
        return self._data.get("Longitude")


class _WiserFirmwareUpgradeItem:
    """Data structure for upgrade info for a Wiser Hub"""

    def __init__(self, data: dict):
        self._data = data

    @property
    def id(self) -> int:
        "Get the id of the firmware filename"
        return self._data.get("id",0)

    @property
    def filename(self) -> str:
        "Get the filename of the firmware file"
        return self._data.get("FirmwareFilename", TEXT_UNKNOWN)


class _WiserFirmareUpgradeInfo:
    """Data structure to hold upgrade file info for a Wiser Hub"""
    def __init__(self, data: dict):
        self._data = data
        self._items = []
        for item in self._data:
            self._items.append(_WiserFirmwareUpgradeItem(item))

    @property
    def all(self) -> dict:
        return self._items

    def by_id(self, id) -> _WiserFirmwareUpgradeItem:
        return [item for item in self._items if item.id == id][0]


class _WiserHubCapabilitiesInfo:
    """Data structure for capabilities info for Wiser Hub"""

    def __init__(self, data: dict):
        self._data = data

    @property
    def all(self) -> str:
        "Get the list of capabilities"
        return self._data
    
    def get_capability(self, name) -> bool:
        """
        Gets a capability value from the hub capabilities
        param name: name of capability
        return: bool
        """
        try:
            return [capability.value for capability in self.capabilities if capability.key == name][0]
        except IndexError:
            return None

    