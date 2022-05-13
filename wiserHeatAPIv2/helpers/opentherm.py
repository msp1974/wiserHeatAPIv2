from .temp import _WiserTemperatureFunctions

class _WiserOpentherm:
    """Data structure for Opentherm data"""
    def __init__(self, data: dict, enabled_status: str):
        self._data = data
        self._enabled_status = enabled_status
        self._operational_data = data.get("operationalData", {})

    @property
    def ch_pressure_bar(self) -> str:
        """Get ChPressureBar operationalData"""
        return self._operational_data.get("ChPressureBar", 0) / 10

    @property
    def ch_flow_temperature(self) -> str:
        """Get Ch1FlowTemperature operationalData"""
        return _WiserTemperatureFunctions._from_wiser_temp(self._operational_data.get("Ch1FlowTemperature", None), "current")

    @property
    def ch_return_temperature(self) -> str:
        """Get ChReturnTemperature operationalData"""
        return _WiserTemperatureFunctions._from_wiser_temp(self._operational_data.get("ChReturnTemperature", None), "current")

    @property
    def connection_status(self) -> str:
        """Get opentherm connection status"""
        return self._enabled_status