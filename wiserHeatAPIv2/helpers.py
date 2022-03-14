from . import _LOGGER
from .const import (
    TEMP_ERROR,
    TEMP_MINIMUM,
    TEMP_MAXIMUM,
    TEMP_OFF,
    TEMP_HW_OFF,
    TEMP_HW_ON,
    TEXT_UNKNOWN,
    MAX_BOOST_INCREASE,
    ROOMSTAT_MIN_BATTERY_LEVEL,
    ROOMSTAT_FULL_BATTERY_LEVEL,
    TRV_MIN_BATTERY_LEVEL,
    TRV_FULL_BATTERY_LEVEL,
    WiserUnitsEnum,
)

class _WiserTemperatureFunctions(object):
    # -----------------------------------------------------------
    # Support Functions
    # -----------------------------------------------------------
    @staticmethod
    def _to_wiser_temp(temp: float, type: str = "set_heating", units:WiserUnitsEnum = WiserUnitsEnum.metric) -> int:
        """
        Converts from degrees C to wiser hub format
        param temp: The temperature to convert
        param type: Can be heating (default), hotwater or delta
        return: Integer
        """
        temp = int(_WiserTemperatureFunctions._validate_temperature(temp, type) * 10)
        
        # Convert to metric if imperial units set
        if units == WiserUnitsEnum.imperial:
            temp = _WiserTemperatureFunctions._convert_from_F(temp)

        return temp

    @staticmethod
    def _from_wiser_temp(temp: int, type: str = "set_heating", units:WiserUnitsEnum = WiserUnitsEnum.metric) -> float:
        """
        Converts from wiser hub format to degrees C
        param temp: The wiser temperature to convert
        return: Float
        """
        if temp is not None:
            if temp >= TEMP_ERROR:  # Fix high value from hub when lost sight of iTRV
                temp = TEMP_MINIMUM
            else:
                temp = _WiserTemperatureFunctions._validate_temperature(round(temp / 10, 1), type)
        
            # Convert to imperial if imperial units set
            if units == WiserUnitsEnum.imperial:
                temp = _WiserTemperatureFunctions._convert_to_F(temp)

            return temp
        return None

    @staticmethod
    def _validate_temperature(temp: float, type: str = "set_heating") -> float:
        """
        Validates temperature value is in range of Wiser Hub allowed values
        Sets to min or max temp if value exceeds limits
        param temp: temperature value to validate
        return: float
        """

        #Accomodate hw temps
        if type == "hotwater" and temp in [TEMP_HW_ON, TEMP_HW_OFF]:
            return temp

        #Accomodate temp deltas
        if type == "delta":
            if temp > MAX_BOOST_INCREASE:
                return MAX_BOOST_INCREASE
            return temp

        # Accomodate reported current temps
        if type == "current":
            if temp < TEMP_OFF:
                return TEMP_MINIMUM
            return temp
        
        #Accomodate heating temps
        if type == "set_heating":
            if temp >= TEMP_ERROR:
                return TEMP_MINIMUM
            elif temp > TEMP_MAXIMUM:
                return TEMP_MAXIMUM
            elif temp < TEMP_MINIMUM and temp != TEMP_OFF:
                return TEMP_MINIMUM
            else:
                return temp

    @staticmethod
    def _convert_from_F(temp: float) -> float:
        """
        Convert F temp to C
        param temp: temp in F to convert
        return: float
        """
        return round((temp - 32) * 5/9, 1)

    @staticmethod
    def _convert_to_F(temp: float) -> float:
        """
        Convert C temp to F
        param temp: temp in C to convert
        return: float
        """
        return round((temp * 9/5) + 32, 1)


class _WiserBattery(object):
    """Data structure for battery information for a Wiser device that is powered by batteries"""

    def __init__(self, data: dict):
        self._data = data

    @property
    def level(self) -> str:
        """Get the descritpion of the battery level"""
        return self._data.get("BatteryLevel", "No Battery")

    @property
    def percent(self) -> int:
        """Get the percent of battery remaining"""
        if self._data.get("ProductType") == "RoomStat" and self.level != "No Battery":
            return min(
                100,
                round(
                    (
                        (self.voltage - ROOMSTAT_MIN_BATTERY_LEVEL)
                        / (ROOMSTAT_FULL_BATTERY_LEVEL - ROOMSTAT_MIN_BATTERY_LEVEL)
                    )
                    * 100
                ),
            )
        elif self._data.get("ProductType") == "iTRV" and self.level != "No Battery":
            return min(
                100,
                round(
                    (
                        (self.voltage - TRV_MIN_BATTERY_LEVEL)
                        / (TRV_FULL_BATTERY_LEVEL - TRV_MIN_BATTERY_LEVEL)
                    )
                    * 100
                ),
            )
        else:
            return 0

    @property
    def voltage(self) -> float:
        """Get the battery voltage"""
        return self._data.get("BatteryVoltage", 0) / 10



class _WiserSignalStrength(object):
    """Data structure for zigbee signal information for a Wiser device"""

    def __init__(self, data: dict):
        self._data = data

    @property
    def displayed_signal_strength(self) -> str:
        """Get the description of signal strength"""
        return self._data.get("DisplayedSignalStrength", TEXT_UNKNOWN)

    @property
    def controller_reception_lqi(self) -> int:
        """Get the signal lqi (quality) for the controller"""
        return self._data.get("ReceptionOfController", {"Lqi": 0}).get("Lqi", None)

    @property
    def controller_reception_rssi(self) -> int:
        """Get the rssi (strength) of the controller signal"""
        return self._data.get("ReceptionOfController", {"Rssi": 0}).get("Rssi", None)

    @property
    def controller_signal_strength(self) -> int:
        """Get the signal strength percent for the device"""
        return min(100, int(2 * (self.controller_reception_rssi + 100))) if self.controller_reception_rssi != 0 else 0

    @property
    def device_reception_lqi(self) -> int:
        """Get the signal lqi (quality) for the device"""
        return self._data.get("ReceptionOfDevice", {"Lqi": 0}).get("Lqi", None)
    
    @property
    def device_reception_rssi(self) -> int:
        """Get the rssi (strength) of the device signal"""
        return self._data.get("ReceptionOfDevice", {"Rssi": 0}).get("Rssi", None)

    @property
    def device_signal_strength(self) -> int:
        """Get the signal strength percent for the device"""
        return min(100, int(2 * (self.device_reception_rssi + 100))) if self.device_reception_rssi != 0 else 0


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
    def signal_rssi_min(self) -> int:
        """Get the wifi signal min rssi value"""
        return self._data.get("RSSI", {}).get("Min", 0)

    @property
    def signal_rssi_max(self) -> int:
        """Get the wifi signal max rssi value"""
        return self._data.get("RSSI", {}).get("Max", 0)

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
    def all(self) -> dict:
        "Get the list of capabilities"
        return dict(self._data)

    @property
    def smartplug(self):
        return self._data.get("SmartPlug", False)

    @property
    def itrv(self):
        return self._data.get("ITRV", False)

    @property
    def roomstat(self):
        return self._data.get("Roomstat", False)

    @property
    def ufh(self):
        return self._data.get("UFH", False)

    @property
    def ufh_floor_temp_sensor(self):
        return self._data.get("UFHFloorTempSensor", False)

    @property
    def ufh_dew_sensor(self):
        return self._data.get("UFHDewSensor", False)

    @property
    def hact(self):
        return self._data.get("HACT", False)

    @property
    def lact(self):
        return self._data.get("LACT", False)

    @property
    def light(self):
        return self._data.get("Light", False)

    @property
    def shutter(self):
        return self._data.get("Shutter", False)

    @property
    def load_controller(self):
        return self._data.get("LoadController", False)
    


    
