from concurrent.futures.process import _threads_wakeups
import enum
import json
import time
from datetime import datetime

from ruamel.yaml import YAML

from . import _LOGGER
from .const import (DEFAULT_LEVEL_SCHEDULE, SPECIAL_DAYS, SPECIAL_TIMES, TEMP_MINIMUM, TEMP_OFF, TEXT_DEGREESC,
                    TEXT_HEATING, TEXT_LEVEL, TEXT_LIGHTING, TEXT_OFF, TEXT_ON, TEXT_ONOFF, TEXT_SETPOINT, TEXT_SHUTTERS, TEXT_STATE,
                    TEXT_TEMP, TEXT_TIME, TEXT_UNKNOWN, TEXT_WEEKDAYS,
                    TEXT_WEEKENDS, WEEKDAYS, WEEKENDS)
from .helpers.temp import _WiserTemperatureFunctions as tf
from .rest_controller import _WiserRestController, WiserRestActionEnum

class WiserScheduleTypeEnum(enum.Enum):
    heating = TEXT_HEATING
    onoff = TEXT_ONOFF
    level = TEXT_LEVEL
    lighting = TEXT_LIGHTING
    shutters = TEXT_SHUTTERS

class _WiserSchedule(object):
    """Class representing a wiser Schedule"""

    def __init__(self, wiser_rest_controller:_WiserRestController, schedule_type: str, schedule_data: dict, sunrises, sunsets):
        self._wiser_rest_controller = wiser_rest_controller
        self._type = schedule_type
        self._schedule_data = schedule_data
        self._sunrises = sunrises
        self._sunsets = sunsets
        self._assignments = []
        self._device_ids = []

    def _validate_schedule_type(self, schedule_data: dict) -> bool:
        return True if schedule_data.get("Type", None) == self.schedule_type or schedule_data.get("SubType", None) == self.schedule_type  else False

    def _is_valid_time(self, time_value: str) -> bool:
        try:
            time.strptime(time_value, "%H:%M")
            return True
        except ValueError:
            return False

    def _ensure_type(self, schedule_data: dict) -> dict:
        if not schedule_data.get("Type"):
            schedule_data["Type"] = self.schedule_type
        return schedule_data

    def _remove_schedule_elements(self, schedule_data: dict) -> dict:
        remove_list = ["id", "CurrentSetpoint", "CurrentState", "Description", "CurrentLevel", "Name", "Next", "Type"]
        for item in remove_list:
            if item in schedule_data:
                del schedule_data[item]
        return schedule_data

    def _convert_from_wiser_schedule(self, schedule_data: dict, replace_special_times: bool = False, generic_setpoint: bool = False) -> dict:
        """
        Convert from wiser format to format suitable for yaml output
        param: scheduleData
        param: mode
        """
        # Create dict to take converted data
        schedule_output = {
            "Name": self.name,
            "Description": self.schedule_type + " schedule for " + self.name,
            "Type": self.schedule_type,
        }
        # Iterate through each day
        try:
            for day, sched in schedule_data.items():
                if day.title() in (WEEKDAYS + WEEKENDS + SPECIAL_DAYS):
                    schedule_set_points = self._convert_wiser_to_yaml_day(
                        day, sched, replace_special_times, generic_setpoint
                    )
                    schedule_output.update({day.capitalize(): schedule_set_points})
            return schedule_output
        except Exception as ex:
            _LOGGER.error(f"Error converting from Wiser schedule: {ex}")
            return None

    def _convert_to_wiser_schedule(self, schedule_data: dict) -> dict:
        """
        Convert from wiser format to format suitable for yaml output
        param: scheduleData
        param: mode
        """
        schedule_output = {}
        try:
            for day, sched in schedule_data.items():
                if day.title() in (WEEKDAYS + WEEKENDS + SPECIAL_DAYS):
                    schedule_day = self._convert_yaml_to_wiser_day(sched)
                    # If using spec days, convert to one entry for each weekday
                    if day.title() in SPECIAL_DAYS:
                        if day.title() == TEXT_WEEKDAYS:
                            for weekday in WEEKDAYS:
                                schedule_output.update({weekday: schedule_day})
                        if day.title() == TEXT_WEEKENDS:
                            for weekend_day in WEEKENDS:
                                schedule_output.update({weekend_day: schedule_day})
                    else:
                        schedule_output.update({day: schedule_day})
            return schedule_output
        except Exception as ex:
            _LOGGER.error(f"Error converting from Wiser schedule: {ex}")
            return None

    
    def _send_schedule_command(self, action: str, schedule_data: dict, id: int = 0) -> bool:
        """
        Send schedule command to Wiser Hub
        param schedule_data: json schedule data
        param id: schedule id
        return: boolen - true = success, false = failed
        """
        try:
            result = self._wiser_rest_controller._send_schedule_command(action, schedule_data, (id if id != 0 else self.id), self._type)
            return result
        except Exception as ex:
            _LOGGER.debug(ex)
            raise

    @property
    def assignments(self):
        """Get ids and names of rooms/devices schedule assigned to"""
        return self._assignments

    @property
    def assignment_ids(self):
        if self._assignments:
            return [assignment.get("id") for assignment in self._assignments]
        return []

    @property
    def assignment_names(self):
        if self._assignments:
            return [assignment.get("name") for assignment in self._assignments]
        return []

    @property
    def current_setting(self) -> str:
        """Get current scheduled setting (temp or state)"""
        if self._type == WiserScheduleTypeEnum.heating.value:
            return tf._from_wiser_temp(self._schedule_data.get("CurrentSetpoint", TEMP_MINIMUM))
        if self._type == WiserScheduleTypeEnum.onoff.value:
            return self._schedule_data.get("CurrentState", TEXT_UNKNOWN)
        if self._type == WiserScheduleTypeEnum.level.value:
            return self._schedule_data.get("CurrentLevel", TEXT_UNKNOWN)

    @property
    def id(self) -> int:
        """Get id of schedule"""
        return self._schedule_data.get("id")

    @property
    def name(self) -> str:
        """Get name of schedule"""
        return self._schedule_data.get("Name")

    @name.setter
    def name(self, name: str):
        """Set name of schedule"""
        self._send_schedule_command("UPDATE", {"Name": name}, self.id)

    @property
    def next(self):
        """Get details of next schedule entry"""
        if self._schedule_data.get("Next"):
            return _WiserScheduleNext(self._type, self._schedule_data.get("Next"))

    @property
    def schedule_data(self) -> str:
        """Get json output of schedule data"""
        return self._remove_schedule_elements(self._schedule_data.copy())

    @property
    def ws_schedule_data(self) -> dict:
        """Get formatted schedule data for webservice support"""
        s = self._remove_schedule_elements(self._convert_from_wiser_schedule(self.schedule_data, generic_setpoint=True))
        return {
            "Id": self.id,
            "Name": self.name,
            "Type": self._type,
            "SubType": self.schedule_type,
            "Assignments": self.assignments,
            "ScheduleData": [{"day": a, "slots": s.get(a)} for a in s]
        }

    @property
    def schedule_type(self) -> str:
        """Get schedule type (heating, on/off or level)"""
        return self._type

    def copy_schedule(self, to_id: int) -> bool:
        """
        Copy this schedule to another schedule
        param toId: id of schedule to copy to
        return: boolen - true = successfully set, false = failed to set
        """
        try:
            self._send_schedule_command("UPDATE", self._remove_schedule_elements(self._schedule_data.copy()), to_id)
            return True
        except Exception as ex:
            _LOGGER.error(f"Error copying schedule: {ex}")
            return False

    def delete_schedule(self) -> bool:
        """
        Delete this schedule
        return: bool
        """
        try:
            if self.id != 1000:
                self._send_schedule_command("DELETE", {})
                return True
            else:
                _LOGGER.error("You cannot delete the schedule for HotWater")
                return False
        except Exception as ex:
            _LOGGER.error(f"Error deleting schedule: {ex}")
            return False

    def save_schedule_to_file(self, schedule_file: str) -> bool:
        """
        Save this schedule to a file as json.
        param scheduleFile: file to write schedule to
        return: boolen - true = successfully saved, false = failed to save
        """
        try:
            with open(schedule_file, "w") as file:
                json.dump(self._ensure_type(self._schedule_data), file, indent=4)
            return True
        except Exception as ex:
            _LOGGER.error(f"Error saving schedule to file: {ex}")
            return False

    def save_schedule_to_yaml_file(self, schedule_yaml_file: str) -> bool:
        """
        Save this schedule to a file as yaml.
        param scheduleFile: file to write schedule to
        return: boolen - true = successfully saved, false = failed to save
        """
        try:
            yaml = YAML()
            with open(schedule_yaml_file, "w") as file:
                yaml.dump(self._convert_from_wiser_schedule(self._schedule_data), file)
            return True
        except Exception as ex:
            _LOGGER.error(f"Error saving schedule to yaml file: {ex}")
            return False

    def set_schedule(self, schedule_data: dict) -> bool:
        """
        Set new schedule
        param scheduleData: json data respresenting a schedule
        return: boolen - true = successfully set, false = failed to set
        """
        try:
            self._send_schedule_command("UPDATE", self._remove_schedule_elements(schedule_data))  
            return True
        except Exception as ex:
            _LOGGER.error(f"Error copying schedule: {ex}")
            return False
              

    def set_schedule_from_file(self, schedule_file: str) -> bool:
        """
        Set schedule from file.
        param schedule_file: file of json data respresenting a schedule
        return: boolen - true = successfully set, false = failed to set
        """
        try:
            with open(schedule_file, "r") as file:
                schedule_data = json.load(file)
                if self._validate_schedule_type(schedule_data):
                    self.set_schedule(self._remove_schedule_elements(schedule_data))
                    return True
                else:
                    _LOGGER.error(f"{schedule_data.get('Type', TEXT_UNKNOWN)} is an incorrect schedule type for this device.  It should be a {self.schedule_type} schedule.")
        except Exception as ex:
            _LOGGER.error(f"Error setting schedule from file: {ex}")
            return False

    def set_schedule_from_yaml_file(self, schedule_yaml_file: str) -> bool:
        """
        Set schedule from file.
        param schedule_file: file of yaml data respresenting a schedule
        return: boolen - true = successfully set, false = failed to set
        """
        try:
            yaml = YAML()
            with open(schedule_yaml_file, "r") as file:
                schedule_data = yaml.load(file)
                if self._validate_schedule_type(schedule_data):
                    schedule = self._convert_to_wiser_schedule(schedule_data)
                    self.set_schedule(schedule)
                    return True
                else:
                    _LOGGER.error(f"This is an incorrect schedule type for this device.  It should be a {self.schedule_type} schedule.")
        except Exception as ex:
            _LOGGER.error(f"Error setting schedule from yaml file: {ex}")
            return False

    def set_schedule_from_ws_data(self, schedule_data: dict) -> bool:
        """
        Set schedule from websocket data.
        param schedule: data respresenting a schedule
        return: boolen - true = successfully set, false = failed to set
        """
        try:
            if self._validate_schedule_type(schedule_data):
                schedule_json = {}
                for entry in schedule_data.get("ScheduleData"):
                    schedule_json.update({entry.get("day"): entry.get("slots")})
                schedule = self._convert_to_wiser_schedule(schedule_json)
                self.set_schedule(schedule)
                return True
            else:
                _LOGGER.error(f"{schedule_data.get('Type', TEXT_UNKNOWN)} is an incorrect schedule type for this device.  It should be a {self.schedule_type} schedule.")
        except Exception as ex:
            _LOGGER.error(f"Error setting schedule from websocket data: {ex}")
            return False

class _WiserHeatingSchedule(_WiserSchedule):
    """ Class for Wiser Heating Schedule """
    def __init__(self, wiser_rest_controller:_WiserRestController, schedule_type: str, schedule_data: dict, sunrises, sunsets):
        super().__init__(wiser_rest_controller, schedule_type, schedule_data, sunrises, sunsets)

    def assign_schedule(self, room_ids: list, include_current: bool = True) -> bool:
        """
        Assign schedule to rooms
        param room_ids: ids of rooms to assign schedule to
        return: bool
        """
        if not isinstance(room_ids, list):
            room_ids = [room_ids]
        if include_current:
            room_ids = room_ids + self.assignment_ids
        schedule_data = {
            "Assignments": list(set(room_ids)),
            self.schedule_type:
                {
                    "id": self.id,
                    "Name": self.name
                }
            }

        try:
            self._send_schedule_command("ASSIGN", schedule_data)
        except Exception as ex:
            _LOGGER.error(f"Error assigning schedule: {ex}")
            return False

    def unassign_schedule(self, room_ids: list):
        if not isinstance(room_ids, list):
            room_ids = [room_ids]
        
        remaining_rooms_ids = []
        if room_ids and self.assignment_ids:
            remaining_rooms_ids = [room_id for room_id in self.assignment_ids if room_id not in room_ids]
        self.assign_schedule(remaining_rooms_ids, False)


    def _convert_wiser_to_yaml_day(self, day, day_schedule, replace_special_times: bool = False, generic_setpoint: bool = False) -> list:
        """
        Convert from wiser schedule format to format for yaml output.
        param daySchedule: json schedule for a day in wiser v2 format
        return: json
        """
        schedule_set_points = []
        for i in range(len(day_schedule[TEXT_TIME])):
            schedule_set_points.append(
                {
                    TEXT_TIME: (
                        datetime.strptime(
                            format(day_schedule[TEXT_TIME][i], "04d"), "%H%M"
                        )
                    ).strftime("%H:%M"),
                    (TEXT_SETPOINT if generic_setpoint else TEXT_TEMP): tf._from_wiser_temp(day_schedule[TEXT_DEGREESC][i]),
                }
            )
        return sorted(schedule_set_points, key=lambda t: t['Time'])

    def _convert_yaml_to_wiser_day(self, day_schedule) -> list:
        """
        Convert from yaml format to wiser v2 schedule format.
        param daySchedule: json schedule for a day in yaml format
        return: json
        """
        times = []
        temps = []

        for item in day_schedule:
            for key, value in item.items():
                if key.title() == TEXT_TIME:
                    time = str(value).replace(":", "")
                    times.append(time)
                if key.title() in [TEXT_TEMP, TEXT_SETPOINT]:
                    temp = tf._to_wiser_temp(
                        float(value) if str(value).title() != TEXT_OFF else TEMP_OFF
                    )
                    temps.append(temp)
        return {TEXT_TIME: times, TEXT_DEGREESC: temps}


class _WiserOnOffSchedule(_WiserSchedule):
    """ Class for Wiser OnOff Schedule """# System Object
    def __init__(self, wiser_rest_controller:_WiserRestController, schedule_type: str, schedule_data: dict, sunrises, sunsets):
        super().__init__(wiser_rest_controller, schedule_type, schedule_data, sunrises, sunsets)
        self._device_type_ids = []

    @property
    def device_type_ids(self):
        """
        Get device type ids of devices schedule attached to.
        Lights and Shutters have 2 ids and need to use Light ID or Shutter ID for schedule control
        Smartplugs will have same id as device id
        """
        return self._device_type_ids

    def assign_schedule(self, device_ids: list, include_current: bool = True) -> bool:
        """
        Assign schedule to devices
        param device_ids: ids of devices to assign schedule to
        return: bool
        """
        if not isinstance(device_ids, list):
            device_ids = [device_ids]
        if include_current:
            device_ids = device_ids + self.assignment_ids
        schedule_data = {
            "Assignments": list(set(device_ids)),
            self.schedule_type:
                {
                    "id": self.id,
                    "Name": self.name
                }
            }

        try:
            self._send_schedule_command("ASSIGN", schedule_data)
        except Exception as ex:
            _LOGGER.error(f"Error assigning schedule: {ex}")
            return False

    def unassign_schedule(self, device_ids: list):
        if not isinstance(device_ids, list):
            device_ids = [device_ids]

        remaining_device_ids = []
        if device_ids and self.assignment_ids:
                remaining_device_ids = [device_id for device_id in self.assignment_ids if device_id not in device_ids]
        self.assign_schedule(remaining_device_ids, False)

    def _convert_wiser_to_yaml_day(self, day, day_schedule, replace_special_times: bool = False, generic_setpoint: bool = False) -> list:
        """
        Convert from wiser schedule format to format for yaml output.
        param daySchedule: json schedule for a day in wiser v2 format
        return: json
        """
        schedule_set_points = []
        for i in range(len(day_schedule)):
            schedule_set_points.append(
                {
                    TEXT_TIME: (
                        datetime.strptime(
                            format(abs(day_schedule[i] if abs(day_schedule[i]) < 2400 else 0), "04d"), "%H%M"
                        )
                    ).strftime("%H:%M"),
                    (TEXT_SETPOINT if generic_setpoint else TEXT_STATE): TEXT_ON if day_schedule[i] == abs(day_schedule[i]) else TEXT_OFF,
                }
            )
        return sorted(schedule_set_points, key=lambda t: t['Time'])

    def _convert_yaml_to_wiser_day(self, day_schedule) -> list:
        """
        Convert from yaml format to wiser v2 schedule format.
        param daySchedule: json schedule for a day in yaml format
        return: json
        """
        times = []

        for entry in day_schedule:
            try:
                if self._is_valid_time(entry.get("Time")):
                    time = int(str(entry.get("Time")).replace(":", ""))
                    time = time if time != 0 else 2400
                else:
                    time = 0
                if entry.get("State", entry.get(TEXT_SETPOINT)).title() == TEXT_OFF:
                    time = -abs(time) if time != 0 else -2400
            except Exception as ex:
                _LOGGER.debug(ex)
                time = 0
            times.append(time)
        return times


class _WiserLevelSchedule(_WiserSchedule):
    """ 
        Class for Wiser Level Schedule
        Lights and Shutters have 2 ids and need to use Light ID or Shutter ID for schedule control
    """
    def __init__(self, wiser_rest_controller:_WiserRestController, schedule_type: str, schedule_data: dict, sunrises, sunsets):
        super().__init__(wiser_rest_controller, schedule_type, schedule_data, sunrises, sunsets)


    @property
    def level_type(self) -> str:
        """Get schedule type level sub type"""
        return self._schedule_data.get("Type", TEXT_UNKNOWN)

    @property
    def level_type_id(self) -> int:
        """Get the schedule level type id"""
        return (2 if self.level_type == WiserScheduleTypeEnum.shutters.value else 1)
    
    @property
    def next(self):
        """Get details of next schedule entry"""
        if self._schedule_data.get("Next"):
            return _WiserScheduleNext(self._type, self._schedule_data.get("Next", {"Day":"", "Time":0, "Level":0}))

    @property
    def schedule_data(self) -> str:
        """Get json output of schedule data"""
        """ Fix for issue of level scheudle can be empty"""
        schedule_data = self._remove_schedule_elements(self._schedule_data.copy())
        if schedule_data:
            return schedule_data
        return DEFAULT_LEVEL_SCHEDULE

    @property
    def schedule_type(self) -> str:
        """Get schedule level type (lighting/shutters)"""
        return self.level_type

    def assign_schedule(self, device_ids: list, include_current: bool = True) -> bool:
        """
        Assign schedule to devices
        param device_ids: ids of devices to assign schedule to
        return: bool
        """
        if not isinstance(device_ids, list):
            device_ids = [device_ids]
        if include_current:
            device_ids = device_ids + self.assignment_ids
        
        type_data = {
                    "id": self.id,
                    "Name": self.name,
                    "Type": self.level_type_id,
        }
        type_data.update(self.schedule_data)
        schedule_data = {
            "Assignments": list(set(device_ids)),
            self._type: type_data
            }

        try:
            self._send_schedule_command("ASSIGN", schedule_data)
        except Exception as ex:
            _LOGGER.error(f"Error assigning schedule: {ex}")
            return False

    def unassign_schedule(self, device_ids: list):
        if not isinstance(device_ids, list):
            device_ids = [device_ids]
        
        if device_ids and self.assignment_ids:
                remaining_device_ids = [device_id for device_id in self.assignment_ids if device_id not in device_ids]
        self.assign_schedule(remaining_device_ids, False)


    def _convert_wiser_to_yaml_day(self, day, day_schedule, replace_special_times: bool = False, generic_setpoint: bool = False) -> list:
        """
        Convert from wiser schedule format to format for yaml output.
        param daySchedule: json schedule for a day in wiser v2 format
        return: json
        """
        schedule_set_points = []
        for i in range(len(day_schedule[TEXT_TIME])):
            if day_schedule[TEXT_TIME][i] in SPECIAL_TIMES.values():
                if replace_special_times:
                    schedule_set_points.append(
                        {
                            TEXT_TIME: (
                                    self._sunrises.get(day) if day_schedule[TEXT_TIME][i] == SPECIAL_TIMES.get("Sunrise") else self._sunsets.get(day)
                                ),
                            (TEXT_SETPOINT if generic_setpoint else TEXT_LEVEL): day_schedule[TEXT_LEVEL][i],
                        }
                    )
                else:
                    schedule_set_points.append(
                        {
                            TEXT_TIME: (
                                    [name for name, time in SPECIAL_TIMES.items() if time == day_schedule[TEXT_TIME][i]][0]
                                ),
                            (TEXT_SETPOINT if generic_setpoint else TEXT_LEVEL): day_schedule[TEXT_LEVEL][i],
                        }
                    )
            else:
                schedule_set_points.append(
                    {
                        TEXT_TIME: (
                            datetime.strptime(
                                format(day_schedule[TEXT_TIME][i], "04d"), "%H%M"
                            )
                        ).strftime("%H:%M"),
                        (TEXT_SETPOINT if generic_setpoint else TEXT_LEVEL): day_schedule[TEXT_LEVEL][i],
                    }
                )
        #Sort list into time order
        return sorted(schedule_set_points, key=lambda t: t['Time'])

    def _convert_yaml_to_wiser_day(self, day_schedule) -> list:
        """
        Convert from yaml format to wiser v2 schedule format.
        param daySchedule: json schedule for a day in yaml format
        return: json
        """
        times = []
        levels = []
        for entry in day_schedule:
            for key, value in entry.items():
                if key.title() == TEXT_TIME:
                    if value.title() in SPECIAL_TIMES.keys():
                        time = SPECIAL_TIMES[value.title()]
                    else:
                        if self._is_valid_time(value):
                            time = str(value).replace(":", "")
                        else:
                            time = "0"
                    times.append(time)
                if key.title() in [TEXT_LEVEL, TEXT_SETPOINT]:
                    levels.append(int(value))
        return {TEXT_TIME: times, TEXT_LEVEL: levels}


class _WiserScheduleNext:
    """Data structure for schedule next entry data"""

    def __init__(self, schedule_type: str, data: dict):
        self._schedule_type = schedule_type
        self._data = data

    @property
    def day(self) -> str:
        """Get the next entry day of the week"""
        return self._data.get("Day", "")

    @property
    def time(self) -> datetime:
        """Get the next entry time"""
        t = f'{self._data.get("Time", 0):04}'
        return datetime.strptime(t[:2] + ':' + t[-2:], '%H:%M').time()

    @property
    def setting(self) -> str:
        """Get the next entry setting - temp for heating, state for on/off devices"""
        if self._schedule_type == TEXT_HEATING:
            return tf._from_wiser_temp(self._data.get("DegreesC"))
        if self._schedule_type == TEXT_ONOFF:
            return self._data.get("State")
        if self._schedule_type == TEXT_LEVEL:
            return self._data.get("Level")
        return None


class _WiserScheduleCollection(object):
    """Class holding all wiser schedule objects"""

    def __init__(self, wiser_rest_controller: _WiserRestController, schedule_data: dict, sunrises, sunsets):
        self._wiser_rest_controller = wiser_rest_controller
        self._sunrises = sunrises
        self._sunsets = sunsets
        self._heating_schedules = []
        self._onoff_schedules = []
        self._level_schedules = []

        self._build(schedule_data)

    def _build(self, schedule_data):
        for schedule_type in schedule_data:
            for schedule in schedule_data.get(schedule_type):
                if schedule_type == WiserScheduleTypeEnum.heating.value:
                    self._heating_schedules.append(_WiserHeatingSchedule(self._wiser_rest_controller, schedule_type, schedule, self._sunrises, self._sunsets))
                if schedule_type == WiserScheduleTypeEnum.onoff.value:
                    self._onoff_schedules.append(_WiserOnOffSchedule(self._wiser_rest_controller, schedule_type, schedule, self._sunrises, self._sunsets))
                if schedule_type == WiserScheduleTypeEnum.level.value:
                    self._level_schedules.append(_WiserLevelSchedule(self._wiser_rest_controller, schedule_type, schedule, self._sunrises, self._sunsets))

    def _send_schedule_command(self, action: str, schedule_data: dict, id: int = 0) -> bool:
        """
        Send schedule command to Wiser Hub
        param schedule_data: json schedule data
        param id: schedule id
        return: boolen - true = success, false = failed
        """
        try:
            result = self._wiser_rest_controller._send_schedule_command(action, schedule_data, id)
            return result
        except Exception as ex:
            _LOGGER.debug(ex)
            raise

    @property
    def all(self) -> list:
        return (
            list(self._heating_schedules)
            + list(self._onoff_schedules)
            + list(self._level_schedules)
        )

    @property
    def count(self) -> int:
        return len(self.all)

    @property
    def heating_schedules(self) -> list:
        return self._heating_schedules

    @property
    def level_schedules(self) -> list:
        return self._level_schedules

    @property
    def onoff_schedules(self) -> list:
        return self._onoff_schedules

    def get_by_id(self, schedule_type: WiserScheduleTypeEnum, id: int) -> _WiserSchedule:
        """
        Gets a schedule object from the schedules id
        param id: id of schedule
        return: _WiserSchedule object
        """
        if schedule_type in [WiserScheduleTypeEnum.lighting, WiserScheduleTypeEnum.shutters]: schedule_type = WiserScheduleTypeEnum.level
        try:
            if schedule_type == WiserScheduleTypeEnum.level:
                return [schedule for schedule in self.all if schedule._type == schedule_type.value and schedule.id == id][0]
            return [schedule for schedule in self.all if schedule.schedule_type == schedule_type.value and schedule.id == id][0]
        except IndexError:
            return None

    def get_by_room_id(self, room_id: int) -> list:
        try:
            return [schedule for schedule in self._heating_schedules if room_id in [schedule.room_ids]][0]
        except IndexError:
            return None

    def get_by_device_id(self, device_id: int) -> list:
        try:
            return [schedule for schedule in self._onoff_schedules + self._level_schedules if device_id in [schedule._device_ids]][0]
        except IndexError:
            return None

    def get_by_name(self, schedule_type: WiserScheduleTypeEnum, name: str) -> _WiserSchedule:
        """
        Gets a schedule object from the schedules name
        (room name, smart plug name, hotwater)
        param name: name of schedule
        return: _WiserSchedule object
        """
        try:
            if schedule_type == WiserScheduleTypeEnum.level:
                return [schedule for schedule in self.all if schedule._type == schedule_type.value and schedule.name == name][0]
            return [schedule for schedule in self.all if schedule.schedule_type == schedule_type and schedule.name == name][0]
        except IndexError:
            return None

    def get_by_type(self, schedule_type: WiserScheduleTypeEnum) -> list:
        """
        Gets a list of schedules that match the schedule type
        param schedule_type: type of schedule mathcing WiserScheduleTypeEnum
        return: list of _WiserSchedule objects
        """
        if schedule_type == WiserScheduleTypeEnum.heating:
            return self._heating_schedules
        if schedule_type == WiserScheduleTypeEnum.onoff:
            return self._onoff_schedules
        if schedule_type == WiserScheduleTypeEnum.level:
            return self._level_schedules
        
        return [schedule for schedule in self.all if schedule.schedule_type == schedule_type]

    def copy_schedule(self, schedule_type: WiserScheduleTypeEnum, from_id: int, to_id:int) -> bool:
        """
        Copy schedule of same type between schedule Ids
        param from_id: id of the schedule to copy
        param to_id: id of the schedule to copy to
        return: True if succeeded, false if failed
        """
        from_schedule = self.get_by_id(schedule_type, from_id)
        to_schedule = self.get_by_id(schedule_type, to_id)

        if from_schedule and to_schedule:
            if from_schedule.schedule_type == to_schedule.schedule_type:
                return from_schedule.copy_schedule(to_id)
            else:
                _LOGGER.error(f"You cannot copy from {from_schedule.schedule_type} to {to_schedule.schedule_type} schedules.  They must be of the same type")
        else:
            _LOGGER.error(f"Invalid schedule id for {'from_id' if not from_schedule else 'to_id'}")
        return False

    def create_schedule(self, schedule_type: WiserScheduleTypeEnum, name: str, assignments: list = []):
        """
        Create a new schedule entry
        param schedule_type: type of schedule to create
        param name: name of schedule
        param assignments: optional - assign new schedule to list of rooms or devices
        """
        type_data = {"Name": name}
        if schedule_type in [WiserScheduleTypeEnum.lighting, WiserScheduleTypeEnum.level]:
            type_data.update({"Type": 1})
            type_data.update(DEFAULT_LEVEL_SCHEDULE)
            schedule_type = WiserScheduleTypeEnum.level
            
        if schedule_type == WiserScheduleTypeEnum.shutters:
            type_data.update({"Type": 2})
            type_data.update(DEFAULT_LEVEL_SCHEDULE)
            schedule_type = WiserScheduleTypeEnum.level

        schedule_data = {
            "Assignments": assignments,
            schedule_type.value: type_data
            }

        self._send_schedule_command("CREATE", schedule_data)


