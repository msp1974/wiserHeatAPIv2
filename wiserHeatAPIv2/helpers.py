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
    def _to_wiser_temp(temp: float, type: str = "heating", units:WiserUnitsEnum = WiserUnitsEnum.metric) -> int:
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
    def _from_wiser_temp(temp: int, type: str = "heating", units:WiserUnitsEnum = WiserUnitsEnum.metric) -> float:
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
    def _validate_temperature(temp: float, type: str = "heating") -> float:
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
        
        #Accomodate heating temps
        if type == "heating":
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
