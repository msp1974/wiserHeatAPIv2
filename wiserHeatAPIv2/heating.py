from .const import TEXT_UNKNOWN

class _WiserHeating:
    """Class representing a Wiser Heating Channel"""

    def __init__(self, data: dict, rooms: dict):
        self._data = data
        self._rooms = rooms

    @property
    def demand_on_off_output(self):
        """Get the demand output for the heating channel"""
        return self._data.get("DemandOnOffOutput", TEXT_UNKNOWN)

    @property
    def heating_relay_status(self) -> str:
        """Get the state of the heating channel relay"""
        return self._data.get("HeatingRelayState", TEXT_UNKNOWN)

    @property
    def id(self) -> int:
        """Get the id of the heating channel"""
        return self._data.get("id")

    @property
    def is_smart_valve_preventing_demand(self) -> bool:
        """Get if a smart valve is preventing demand for heating channel"""
        return self._data.get("IsSmartValvePreventingDemand", False)

    @property
    def name(self) -> str:
        """Get the name of the heating channel"""
        return self._data.get("Name", TEXT_UNKNOWN)

    @property
    def percentage_demand(self) -> int:
        """Get the percentage demand of the heating channel"""
        return self._data.get("PercentageDemand", 0)

    @property
    def rooms(self):
        """Get the rooms attached to this heating channel"""
        rooms = []
        for room in self._rooms:
            if room.id in self.room_ids:
                rooms.append(room)
        return rooms

    @property
    def room_ids(self):
        """Get a list of the room ids attached to this heating channel"""
        return self._data.get("RoomIds", [])