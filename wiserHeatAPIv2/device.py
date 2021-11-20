from .const import TEXT_UNKNOWN

class _WiserDevice(object):
    """Class representing a wiser device"""

    def __init__(self, data: dict):
        self._data = data
        self._signal = _WiserSignalStrength(data)

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

    @property
    def signal(self) -> object:
        """Get zwave network information"""
        return self._signal



class _WiserSignalStrength(object):
    """Data structure for zigbee signal information for a Wiser device"""

    def __init__(self, data: dict):
        self._data = data

    @property
    def displayed_signal_strength(self) -> str:
        """Get the description of signal strength"""
        return self._data.get("DisplayedSignalStrength", TEXT_UNKNOWN)

    @property
    def controller_reception_rssi(self) -> int:
        """Get the rssi (strength) of the controller signal"""
        return self._data.get("ReceptionOfController", {"Rssi": 0}).get("Rssi", None)

    @property
    def device_reception_rssi(self) -> int:
        """Get the rssi (strength) of the device signal"""
        return self._data.get("ReceptionOfDevice", {"Rssi": 0}).get("Rssi", None)

    @property
    def controller_reception_lqi(self) -> int:
        """Get the signal lqi (quality) for the controller"""
        return self._data.get("ReceptionOfController", {"Lqi": 0}).get("Lqi", None)

    @property
    def device_reception_lqi(self) -> int:
        """Get the signal lqi (quality) for the device"""
        return self._data.get("ReceptionOfDevice", {"Lqi": 0}).get("Lqi", None)

    @property
    def signal_strength(self) -> int:
        """Get the signal strength percent for the device"""
        return min(100, int(2 * (self.controller_reception_rssi + 100)))