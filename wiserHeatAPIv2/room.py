from . import _LOGGER
import enum

from .devices import _WiserDeviceCollection
from .helpers import _WiserTemperatureFunctions as tf
from .schedule import _WiserSchedule, _WiserScheduleCollection
from .rest_controller import _WiserRestController

from .const import (
    TEMP_MINIMUM,
    TEMP_MAXIMUM,
    TEMP_OFF,
    TEXT_AUTO,
    TEXT_MANUAL,
    TEXT_OFF,
    TEXT_ON,
    TEXT_UNKNOWN,
    WISERROOM
)

class WiserHeatingModeEnum(enum.Enum):
    off = TEXT_OFF
    auto = TEXT_AUTO
    manual = TEXT_MANUAL


from datetime import datetime, timezone
import inspect


class _WiserRoom(object):
    """Class representing a Wiser Room entity"""

    def __init__(self, wiser_rest_controller:_WiserRestController, room: dict, schedule: _WiserSchedule, devices: list):
        self._wiser_rest_controller = wiser_rest_controller
        self._data = room
        self._schedule = schedule
        self._devices = devices
        self._mode = self._effective_heating_mode(
            self._data.get("Mode"), 
            self.current_target_temperature
        )
        self._name = room.get("Name")
        self._window_detection_active = room.get("WindowDetectionActive", TEXT_UNKNOWN)

    def _effective_heating_mode(self, mode: str, temp: float) -> str:
        if mode.casefold() == TEXT_MANUAL.casefold() and temp == TEMP_OFF:
            return TEXT_OFF
        elif mode.casefold() == TEXT_MANUAL.casefold():
            return TEXT_MANUAL
        return TEXT_AUTO

    def _send_command(self, cmd: dict):
        """
        Send control command to the room
        param cmd: json command structure
        return: boolen
        """
        result = self._wiser_rest_controller._send_command(WISERROOM.format(self.id), cmd)
        if result:
            _LOGGER.debug(
                "Wiser room - {} command successful - {}".format(inspect.stack()[1].function, result)
            )
        return result

    @property
    def available_modes(self) -> str:
        """Get available heating modes"""
        return [mode.value for mode in WiserHeatingModeEnum]

    @property
    def away_mode_suppressed(self) -> str:
        """Get if away mode is suppressed for room"""
        return self._data.get("AwayModeSuppressed", TEXT_UNKNOWN)

    @property
    def boost_end_time(self) -> datetime:
        """Get boost end timestamp"""
        if self._data.get("OverrideTimeoutUnixTime", 0) == 0:
            return None
        return datetime.fromtimestamp(self._data.get("OverrideTimeoutUnixTime", 0))

    @property
    def boost_time_remaining(self) -> datetime:
        """Get boost time remaining"""
        if self.is_boosted:
            return (self.boost_end_time - datetime.now()).total_seconds()
        else:
            return 0

    @property
    def current_target_temperature(self) -> float:
        """Get current target temperature for the room"""
        return tf._from_wiser_temp(self._data.get("CurrentSetPoint", TEMP_MINIMUM))

    @property
    def current_temperature(self) -> float:
        """Get current temperature of the room"""
        return tf._from_wiser_temp(self._data.get("CalculatedTemperature", TEMP_MINIMUM))

    @property
    def current_humidity(self) -> int:
        """Get current humidity of the room if room has a roomstat"""
        for device in self.devices:
            if hasattr(device, "current_humidity"):
                return device.current_humidity
        return None

    @property
    def devices(self) -> list:
        """Get devices associated with the room"""
        return self._devices

    @property
    def heating_rate(self) -> str:
        """Get room heating rate"""
        return self._data.get("HeatingRate", TEXT_UNKNOWN)

    @property
    def id(self) -> int:
        """Get the id of the room"""
        return self._data.get("id")

    @property
    def is_away_mode(self) -> bool:
        """Get if the room temperature is currently set by away mode"""
        return (
            True
            if "Away" in self._data.get("SetpointOrigin", self._data.get("SetPointOrigin", TEXT_UNKNOWN))
            else False
        )

    @property
    def is_boosted(self) -> bool:
        """Get if the room temperature is currently boosted"""
        return (
            True
            if "Boost" in self._data.get("SetpointOrigin", self._data.get("SetPointOrigin",TEXT_UNKNOWN))
            else False
        )

    @property
    def is_override(self) -> bool:
        """Get if the room has an override"""
        return (
            True
            if self._data.get("OverrideType", TEXT_UNKNOWN) not in  [TEXT_UNKNOWN, "None"]
            else False
        )

    @property
    def is_heating(self) -> bool:
        """Get if the room is currently heating"""
        return (
            True if self._data.get("ControlOutputState", TEXT_OFF) == TEXT_ON else False
        )

    @property
    def manual_target_temperature(self) -> float:
        """Get current target temperature for manual mode"""
        return tf._from_wiser_temp(self._data.get("ManualSetPoint", TEMP_MINIMUM))

    @property
    def mode(self) -> str:
        """Get or set current mode for the room (Off, Manual, Auto)"""
        return WiserHeatingModeEnum[self._mode.lower()].value

    @mode.setter
    def mode(self, mode: str):
        if mode.casefold() == WiserHeatingModeEnum.off.value.casefold():
            self.set_manual_temperature(TEMP_OFF)
        elif mode.casefold() == WiserHeatingModeEnum.manual.value.casefold():
            if self._send_command({"Mode": WiserHeatingModeEnum.manual.value}):
                if self.current_target_temperature == TEMP_OFF:
                    self.set_target_temperature(self.scheduled_target_temperature)
        elif mode.casefold() == WiserHeatingModeEnum.auto.value.casefold():
            if self.is_override:
                self.cancel_overrides()
            self._send_command({"Mode": WiserHeatingModeEnum.auto.value})
        else:
            raise ValueError(
                f"{mode} is not a valid Heating mode.  Valid modes are {self.available_modes}"
            )
        self._mode = WiserHeatingModeEnum[mode.lower()].value

    @property
    def name(self) -> str:
        """Get or set the name of the room"""
        return self._name

    @name.setter
    def name(self, name: str):
        if self._send_command({"Name": name.title()}):
            self._name = name.title()

    @property
    def override_target_temperature(self) -> float:
        """Get the override target temperature of the room"""
        return self._data.get("OverrideSetpoint", 0)

    @property
    def override_type(self) -> str:
        """Get the current override type for the room"""
        return self._data.get("OverrideType", "None")

    @property
    def percentage_demand(self) -> int:
        """Get the percentage demand of the room"""
        return self._data.get("PercentageDemand", 0)

    @property
    def schedule(self) -> _WiserSchedule:
        """Get the schedule for the room"""
        return self._schedule

    @property
    def schedule_id(self) -> int:
        """Get the schedule id for the room"""
        return self._data.get("ScheduleId")

    @property
    def scheduled_target_temperature(self) -> float:
        """Get the scheduled target temperature for the room"""
        return tf._from_wiser_temp(self._data.get("ScheduledSetPoint", TEMP_MINIMUM))

    @property
    def target_temperature_origin(self) -> str:
        """Get the origin of the target temperature setting for the room"""
        return self._data.get("SetpointOrigin", self._data.get("SetpointOrigin", TEXT_UNKNOWN))

    @property
    def window_detection_active(self) -> bool:
        """Get or set if window detection is active"""
        return self._window_detection_active

    @window_detection_active.setter
    def window_detection_active(self, enabled: bool):
        if self._send_command({"WindowDetectionActive": enabled}):
            self._window_detection_active = enabled

    @property
    def window_state(self) -> str:
        """
        Get the currently detected window state for the room.
        Window detection needs to be active
        """
        return self._data.get("WindowState", TEXT_UNKNOWN)

    def boost(self, inc_temp: float, duration: int) -> bool:
        """
        Boost the target temperature of the room
        param inc_temp: increase target temperature over current temperature by 0C to 5C
        param duration: the duration to boost the room temperature in minutes
        return: boolean
        """
        if duration == 0:
            return self.cancel_boost()
        return self._send_command(
            {
                "RequestOverride": {
                    "Type": "Boost",
                    "DurationMinutes": duration,
                    "IncreaseSetPointBy": tf._to_wiser_temp(inc_temp, "delta")
                }
            }
        )

    def cancel_boost(self) -> bool:
        """
        Cancel the target temperature boost of the room
        return: boolean
        """
        if self.is_boosted:
            return self.cancel_overrides()
        else:
            return True

    def set_target_temperature(self, temp: float) -> bool:
        """
        Set the target temperature of the room to override current schedule temp or in manual mode
        param temp: the temperature to set in C
        return: boolean
        """
        return self._send_command(
            {
                "RequestOverride": {
                    "Type": "Manual",
                    "SetPoint": tf._to_wiser_temp(temp),
                }
            }
        )

    def set_target_temperature_for_duration(self, temp: float, duration: int) -> bool:
        """
        Set the target temperature of the room to override current schedule temp or in manual mode
        param temp: the temperature to set in C
        return: boolean
        """
        return self._send_command(
            {
                "RequestOverride": {
                    "Type": "Manual",
                    "DurationMinutes": duration,
                    "SetPoint": tf._to_wiser_temp(temp),
                }
            }
        )

    def set_manual_temperature(self, temp: float) -> bool:
        """
        Set the mode to manual with target temperature for the room
        param temp: the temperature to set in C
        return: boolean
        """
        if self.mode != WiserHeatingModeEnum.manual.value:
            self.mode = WiserHeatingModeEnum.manual.value
        return self.set_target_temperature(temp)

    def schedule_advance(self) -> bool:
        """
        Advance room schedule to the next scheduled time and temperature setting
        return: boolean
        """
        if self.cancel_boost():
            return self.set_target_temperature(self.schedule.next.setting)

    def cancel_overrides(self) -> bool:
        """
        Cancel all overrides and set room schedule to the current temperature setting for the mode
        return: boolean
        """
        return self._send_command({"RequestOverride": {"Type": "None"}})


class _WiserRoomCollection(object):
    """Class holding all wiser room objects"""

    def __init__(
        self, wiser_rest_controller: _WiserRestController, room_data: dict,
        schedules: _WiserScheduleCollection, devices: _WiserDeviceCollection
    ):

        self._wiser_rest_controller = wiser_rest_controller
        self._room_data = room_data
        self._schedules = schedules.all
        self._devices = devices
        self._rooms = []

        self._build()

    def _build(self):
        # Add room objects
        for room in self._room_data:
            schedule = [
                schedule
                for schedule in self._schedules
                if schedule.id == room.get("ScheduleId")
            ]
            devices = [
                device
                for device in self._devices.all
                if (
                    device.id in room.get("SmartValveIds", ["-1"])
                    or device.id == room.get("RoomStatId", "-1")
                    or device.id
                    in [
                        smartplug.id
                        for smartplug in self._devices._smartplugs_collection.all
                        if smartplug.room_id == room.get("id", 0)
                    ]
                )
            ]
            self._rooms.append(
                _WiserRoom(
                    self._wiser_rest_controller,
                    room,
                    schedule[0] if len(schedule) > 0 else None,
                    devices,
                )
            )


    @property
    def all(self) -> list:
        """Returns list of room objects"""
        return self._rooms

    @property
    def count(self) -> int:
        """Number of rooms"""
        return len(self._rooms)

    def add(self, name):
        # call domain/room with post and name param
        raise NotImplemented

    def delete(self, id: int):
        # call room/id with delete
        raise NotImplemented

    def get_by_id(self, id: int) -> _WiserRoom:
        """
        Gets a room object for the room by id of room
        param id: the id of the room
        return: _WiserRoom object
        """
        try:
            return [room for room in self._rooms if room.id == id][0]
        except IndexError:
            return None

    def get_by_name(self, name: str) -> _WiserRoom:
        """
        Gets a room object for the room by name of room
        param name: the name of the room
        return: _WiserRoom object
        """
        try:
            return [room for room in self._rooms if room.name.lower() == name.lower()][0]
        except IndexError:
            return None

    def get_by_schedule_id(self, schedule_id: int) -> _WiserRoom:
        """
        Gets a room object for the room a schedule id belongs to
        param schedule_id: the id of the schedule
        return: _WiserRoom object
        """
        return [room for room in self._rooms if room.schedule_id == schedule_id][0]

    def get_by_device_id(self, device_id: int) -> _WiserRoom:
        """
        Gets a room object for the room a device id belongs to
        param device_id: the id of the device
        return: _WiserRoom object
        """
        for room in self._rooms:
            for device in room.devices:
                if device.id == device_id:
                    return room
        return None

    