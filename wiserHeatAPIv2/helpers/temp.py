from ..const import (
    TEMP_ERROR,
    TEMP_MINIMUM,
    TEMP_MAXIMUM,
    TEMP_OFF,
    TEMP_HW_OFF,
    TEMP_HW_ON,
    MAX_BOOST_INCREASE,
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
