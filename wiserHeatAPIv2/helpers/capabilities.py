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