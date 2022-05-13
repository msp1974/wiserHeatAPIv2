class _WiserGPS:
    """Data structure for gps positional information for a Wiser Hub"""

    def __init__(self, data: dict):
        self._data = data

    @property
    def latitude(self) -> float:
        """Get the latitude of the hub"""
        return self._data.get("Latitude")

    @property
    def longitude(self) -> float:
        """Get the longitude of the hub"""
        return self._data.get("Longitude")