from .const import TEXT_UNKNOWN
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
        