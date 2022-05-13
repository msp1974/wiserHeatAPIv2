from ..const import (
    TEXT_UNKNOWN
)

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