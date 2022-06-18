from ..const import (
    TEXT_UNKNOWN
)

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
        return min(
            100, int(2 * (self.controller_reception_rssi + 100))
            ) if self.controller_reception_rssi and self.controller_reception_rssi != 0 else 0

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
        if self.device_reception_rssi:
            return min(100, int(2 * (self.device_reception_rssi + 100))) if self.device_reception_rssi != 0 else 0
        return None