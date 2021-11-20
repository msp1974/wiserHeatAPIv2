from .const import TEXT_UNKNOWN
from .room import _WiserRoomCollection

class _WiserHeatingChannelCollection(object):
    """Class holding all wiser heating channel objects"""

    def __init__(self, heating_channel_data: dict, rooms: _WiserRoomCollection):

        self._heating_channels = []
        self._heating_channel_data = heating_channel_data
        self._rooms = rooms
        
        self._build()

    def _build(self):
        for heat_channel in self._heating_channel_data:
                self._heating_channels.append(_WiserHeatingChannel(heat_channel))

    @property
    def all(self):
        return list(self._heating_channels)

    @property
    def count(self) -> int:
        return len(self.all)

    def get_by_id(self, id: int):
        """
        Gets a Heating Channel object from the Heating Channels id
        param id: id of heating channel
        return: _WiserHeatingChannel object
        """
        for heating_channel in self.all:
            if id == heating_channel.id:
                return heating_channel
        return None

    def get_by_room_id(self, id: int):
        """
        Gets a Heating Channel object from a Room ID
        param id: id of the room
        return: _WiserHeatingChannel object
        """
        for heating_channel in self.all:
            if id in heating_channel.room_ids:
                return heating_channel
        return None

    def get_by_room_name(self, room_name:str):
        """
        Gets a Heating Channel object from a Room Name
        param id: name of the room
        return: _WiserHeatingChannel object
        """
        room = self._rooms.get_by_name(room_name)
        return self.get_by_room_id(room.id)


class _WiserHeatingChannel(object):
    """Class representing a Wiser Heating Channel"""

    def __init__(self, data: dict):
        self._data = data

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
    def room_ids(self) -> list:
        """Get a list of the room ids attached to this heating channel"""
        return self._data.get("RoomIds", None)