from .const import (
    TEMP_ERROR,
    TEMP_MINIMUM,
    TEMP_MAXIMUM,
    TEMP_OFF,
    WiserUnitsEnum
)

# -----------------------------------------------------------
# Support Functions
# -----------------------------------------------------------
def _validate_temperature(temp: float) -> float:
    """
    Validates temperature value is in range of Wiser Hub allowed values
    Sets to min or max temp if value exceeds limits
    param temp: temperature value to validate
    return: float
    """
    if temp >= TEMP_ERROR:
        return TEMP_MINIMUM
    elif temp > TEMP_MAXIMUM:
        return TEMP_MAXIMUM
    elif temp < TEMP_MINIMUM and temp != TEMP_OFF:
        return TEMP_MINIMUM
    else:
        return temp


def _to_wiser_temp(temp: float, units:WiserUnitsEnum = WiserUnitsEnum.metric) -> int:
    """
    Converts from degrees C to wiser hub format
    param temp: The temperature to convert
    return: Integer
    """
    # Convert to metric if imperial units set
    if units == WiserUnitsEnum.imperial:
        temp = _convert_from_F(temp)

    return int(_validate_temperature(temp) * 10)


def _from_wiser_temp(temp: int, units:WiserUnitsEnum = WiserUnitsEnum.metric) -> float:
    """
    Converts from wiser hub format to degrees C
    param temp: The wiser temperature to convert
    return: Float
    """
    if temp is not None:
        if temp >= TEMP_ERROR:  # Fix high value from hub when lost sight of iTRV
            temp = TEMP_MINIMUM
        else:
            temp = round(temp / 10, 1)
    
        # Convert to imperial if imperial units set
        if units == WiserUnitsEnum.imperial:
            temp = _convert_to_F(temp)

        return temp
    return None

def _convert_from_F(temp: float) -> float:
    """
    Convert F temp to C
    param temp: temp in F to convert
    return: float
    """
    return round((temp - 32) * 5/9, 1)

def _convert_to_F(temp: float) -> float:
    """
    Convert C temp to F
    param temp: temp in C to convert
    return: float
    """
    return round((temp * 9/5) + 32, 1)
