from .const import (
    ROOMSTAT_MIN_BATTERY_LEVEL,
    ROOMSTAT_FULL_BATTERY_LEVEL,
    TRV_MIN_BATTERY_LEVEL,
    TRV_FULL_BATTERY_LEVEL,
    TEXT_UNKNOWN
)
from .system import _WiserZwaveSignal

class _WiserDevice(object):
    """Class representing a wiser device"""

    def __init__(self, data: dict):
        self._data = data
        self.signal = _WiserZwaveSignal(data)

    @property
    def firmware_version(self) -> str:
        """Get firmware version of device"""
        return self._data.get("ActiveFirmwareVersion", TEXT_UNKNOWN)

    @property
    def id(self) -> int:
        """Get id of device"""
        return self._data.get("id")

    @property
    def model(self) -> str:
        """Get model of device"""
        return self._data.get("ModelIdentifier", TEXT_UNKNOWN)

    @property
    def node_id(self) -> int:
        """Get zigbee node id of device"""
        return self._data.get("NodeId", 0)

    @property
    def parent_node_id(self) -> int:
        """Get zigbee node id of device this device is connected to"""
        return self._data.get("ParentNodeId", 0)

    @property
    def product_type(self) -> str:
        """Get product type of device"""
        return self._data.get("ProductType", TEXT_UNKNOWN)

    @property
    def serial_number(self) -> str:
        """Get serial number of device"""
        return self._data.get("SerialNumber", TEXT_UNKNOWN)
        

class _WiserBattery:
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
        if self._data.get("ProductType") == "RoomStat":
            return min(
                100,
                int(
                    (
                        (self.voltage - ROOMSTAT_MIN_BATTERY_LEVEL)
                        / (ROOMSTAT_FULL_BATTERY_LEVEL - ROOMSTAT_MIN_BATTERY_LEVEL)
                    )
                    * 100
                ),
            )
        elif self._data.get("ProductType") == "iTRV":
            return min(
                100,
                int(
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