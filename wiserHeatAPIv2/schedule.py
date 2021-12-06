import inspect
import json
from datetime import datetime

from ruamel.yaml import YAML

from . import _LOGGER
from .const import (SPECIAL_DAYS, TEMP_MINIMUM, TEMP_OFF, TEXT_DEGREESC,
                    TEXT_HEATING, TEXT_OFF, TEXT_ON, TEXT_ONOFF, TEXT_STATE,
                    TEXT_TEMP, TEXT_TIME, TEXT_UNKNOWN, TEXT_WEEKDAYS,
                    TEXT_WEEKENDS, WEEKDAYS, WEEKENDS, WISERHUBSCHEDULES)
from .helpers import _WiserTemperatureFunctions as tf
from .rest_controller import _WiserRestController

class _WiserSchedule(object):
    """Class representing a wiser Schedule"""

    def __init__(self, wiser_rest_controller:_WiserRestController, schedule_type: str, schedule_data: dict):
        self._wiser_rest_controller = wiser_rest_controller
        self._type = schedule_type
        self._schedule_data = schedule_data

    def _remove_schedule_elements(self, schedule_data: dict) -> dict:
        remove_list = ["id", "CurrentSetpoint", "CurrentState", "Name", "Next"]
        for item in remove_list:
            if item in schedule_data:
                del schedule_data[item]
        return schedule_data

    def _convert_from_wiser_schedule(self, schedule_data: dict) -> dict:
        """
        Convert from wiser format to format suitable for yaml output
        param: scheduleData
        param: mode
        """
        # Create dict to take converted data
        schedule_output = {
            "Name": self.name,
            "Description": self._type + " schedule for " + self.name,
            "Type": self._type,
        }
        # Iterate through each day
        try:
            for day, sched in schedule_data.items():
                if day.title() in (WEEKDAYS + WEEKENDS + SPECIAL_DAYS):
                    schedule_set_points = self._convert_wiser_to_yaml_day(
                        sched, self._type
                    )
                    schedule_output.update({day.capitalize(): schedule_set_points})
            return schedule_output
        except Exception:
            return None

    def _convert_to_wiser_schedule(self, schedule_yaml_data: dict) -> dict:
        """
        Convert from wiser format to format suitable for yaml output
        param: scheduleData
        param: mode
        """
        schedule_output = {}
        try:
            for day, sched in schedule_yaml_data.items():
                if day.title() in (WEEKDAYS + WEEKENDS + SPECIAL_DAYS):
                    schedule_day = self._convert_yaml_to_wiser_day(sched, self._type)
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
            _LOGGER.error("Error converting to Wiser schedule: {}".format(ex))
            return None

    def _convert_wiser_to_yaml_day(self, day_schedule, schedule_type) -> list:
        """
        Convert from wiser schedule format to format for yaml output.
        param daySchedule: json schedule for a day in wiser v2 format
        param scheduleType: Heating or OnOff
        return: json
        """
        schedule_set_points = []
        if schedule_type == TEXT_HEATING:
            for i in range(len(day_schedule[TEXT_TIME])):
                schedule_set_points.append(
                    {
                        TEXT_TIME: (
                            datetime.strptime(
                                format(day_schedule[TEXT_TIME][i], "04d"), "%H%M"
                            )
                        ).strftime("%H:%M"),
                        TEXT_TEMP: tf._from_wiser_temp(day_schedule[TEXT_DEGREESC][i]),
                    }
                )
        else:
            for i in range(len(day_schedule)):
                schedule_set_points.append(
                    {
                        TEXT_TIME: (
                            datetime.strptime(
                                format(abs(day_schedule[i]), "04d"), "%H%M"
                            )
                        ).strftime("%H:%M"),
                        TEXT_STATE: TEXT_ON if day_schedule[i] > 0 else TEXT_OFF,
                    }
                )
        return schedule_set_points

    def _convert_yaml_to_wiser_day(self, day_schedule, schedule_type) -> list:
        """
        Convert from yaml format to wiser v2 schedule format.
        param daySchedule: json schedule for a day in yaml format
        param scheduleType: Heating or OnOff
        return: json
        """
        times = []
        temps = []

        if schedule_type == TEXT_HEATING:
            for item in day_schedule:
                for key, value in item.items():
                    if key.title() == TEXT_TIME:
                        time = str(value).replace(":", "")
                        times.append(time)
                    if key.title() == TEXT_TEMP:
                        temp = tf._to_wiser_temp(
                            value if str(value).title() != TEXT_OFF else TEMP_OFF
                        )
                        temps.append(temp)
            return {TEXT_TIME: times, TEXT_DEGREESC: temps}
        else:
            for entry in day_schedule:
                try:
                    time = int(str(entry.get("Time")).replace(":", ""))
                    if entry.get("State").title() == TEXT_OFF:
                        time = 0 - int(time)
                except Exception as ex:
                    _LOGGER.debug(ex)
                    time = 0
                times.append(time)
            return times

    def _send_schedule(self, schedule_data: dict, id: int = 0) -> bool:
        """
        Send system control command to Wiser Hub
        param cmd: json command structure
        return: boolen - true = success, false = failed
        """
        try:
            result = self._wiser_rest_controller._send_schedule(
                WISERHUBSCHEDULES
                + "{}/{}".format(self._type, str(id if id != 0 else self.id)),
                schedule_data,
            )
            if result:
                _LOGGER.debug(
                    "Wiser schedule - {} command successful".format(
                        inspect.stack()[1].function
                    )
                )
            return result
        except Exception as ex:
            _LOGGER.debug(ex)

    @property
    def current_setting(self) -> str:
        """Get current scheduled setting (temp or state)"""
        if self._type == "Heating":
            return tf._from_wiser_temp(self._schedule_data.get("CurrentSetpoint", TEMP_MINIMUM))
        if self._type == "OnOff":
            return self._schedule_data.get("CurrentState", TEXT_UNKNOWN)

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
        self._send_schedule(f'{"Name": {name}}', self.id)

    @property
    def next(self):
        """Get details of next schedule entry"""
        return _WiserScheduleNext(self._type, self._schedule_data.get("Next"))

    @property
    def schedule_data(self) -> str:
        """Get json output of schedule data"""
        return self._remove_schedule_elements(self._schedule_data.copy())

    @property
    def schedule_type(self) -> str:
        """Get schedule type (heating or on/off)"""
        return self._type

    def copy_schedule(self, to_id: int) -> bool:
        """
        Copy this schedule to another schedule
        param toId: id of schedule to copy to
        return: boolen - true = successfully set, false = failed to set
        """
        return self._send_schedule(self._remove_schedule_elements(self._schedule_data), to_id)

    def save_schedule_to_file(self, schedule_file: str) -> bool:
        """
        Save this schedule to a file as json.
        param scheduleFile: file to write schedule to
        return: boolen - true = successfully saved, false = failed to save
        """
        try:
            with open(schedule_file, "w") as file:
                json.dump(self._schedule_data, file, indent=4)
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
        return self._send_schedule(self._remove_schedule_elements(schedule_data))

    def set_schedule_from_file(self, schedule_file: str) -> bool:
        """
        Set schedule from file.
        param schedule_file: file of json data respresenting a schedule
        return: boolen - true = successfully set, false = failed to set
        """
        try:
            with open(schedule_file, "r") as file:
                self.set_schedule(self._remove_schedule_elements(json.load(file)))
                return True
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
                y = yaml.load(file)
                s = self._convert_to_wiser_schedule(y)
                self.set_schedule(s)
                return True
        except Exception as ex:
            _LOGGER.error(f"Error setting schedule from yaml file: {ex}")
            return False


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
        return None


class _WiserScheduleCollection(object):
    """Class holding all wiser schedule objects"""

    def __init__(self, wiser_rest_controller, schedule_data: dict):
        self._wiser_rest_controller = wiser_rest_controller
        self._schedules = []

        self._build(schedule_data)

    def _build(self, schedule_data):
        for schedule_type in schedule_data:
            for schedule in schedule_data.get(schedule_type):
                self._schedules.append(_WiserSchedule(self._wiser_rest_controller, schedule_type, schedule))

    @property
    def all(self) -> list:
        return self._schedules

    @property
    def count(self) -> int:
        return len(self.all)

    def get_by_id(self, id: int) -> _WiserSchedule:
        """
        Gets a schedule object from the schedules id
        param id: id of schedule
        return: _WiserSchedule object
        """
        try:
            return [schedule for schedule in self.all if schedule.id == id][0]
        except IndexError:
            return None

    def get_by_name(self, name: str) -> _WiserSchedule:
        """
        Gets a schedule object from the schedules name
        (room name, smart plug name, hotwater)
        param name: name of schedule
        return: _WiserSchedule object
        """
        try:
            return [schedule for schedule in self.all if schedule.name == name][0]
        except IndexError:
            return None
