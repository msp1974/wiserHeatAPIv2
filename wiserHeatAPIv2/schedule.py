from .const import (
    WEEKDAYS,
    WEEKENDS,
    SPECIAL_DAYS,
    TEXT_WEEKDAYS,
    TEXT_WEEKENDS,
    TEXT_HEATING,
    TEXT_TIME,
    TEXT_DEGREESC,
    TEXT_TEMP,
    TEXT_STATE,
    TEXT_OFF,
    TEXT_ON,
    TEXT_ONOFF,
    TEMP_OFF,
    TEXT_UNKNOWN,
    TEMP_MINIMUM,
    WISERHUBSCHEDULES
)
from .rest_controller import _WiserRestController

from .helpers import (
    _to_wiser_temp,
    _from_wiser_temp
)

from datetime import datetime
import inspect
import json
import logging
from ruamel.yaml import YAML

_LOGGER = logging.getLogger(__name__)

class _WiserSchedule(object):
    """Class representing a wiser Schedule"""

    def __init__(self, schedule_type: str, schedule_data: dict):
        self._type = schedule_type
        self._schedule_data = schedule_data

    def _remove_schedule_elements(self, schedule_data: dict):
        remove_list = ["id", "CurrentSetpoint", "CurrentState", "Name", "Next"]
        for item in remove_list:
            if item in schedule_data:
                del schedule_data[item]
        return schedule_data

    def _convert_from_wiser_schedule(self, schedule_data: dict):
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

    def _convert_to_wiser_schedule(self, schedule_yaml_data: dict):
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
        except Exception:
            return None

    def _convert_wiser_to_yaml_day(self, day_schedule, schedule_type):
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
                        TEXT_TEMP: _from_wiser_temp(day_schedule[TEXT_DEGREESC][i]),
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

    def _convert_yaml_to_wiser_day(self, day_schedule, schedule_type):
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
                        temp = _to_wiser_temp(
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
            rest = _WiserRestController()
            result = rest._send_schedule(
                WISERHUBSCHEDULES
                + "{}/{}".format(self._type, str(id if id != 0 else self.id)),
                schedule_data,
            )
            if result:
                _LOGGER.info(
                    "Wiser schedule - {} command successful".format(
                        inspect.stack()[1].function
                    )
                )
            return result
        except Exception as ex:
            _LOGGER.debug(ex)

    # TODO: Decide on seperate properties or single setting or both
    @property
    def current_target_temperature(self) -> float:
        """Get current scheduled target temperature for heating device"""
        return _from_wiser_temp(
            self._schedule_data.get("CurrentSetpoint", TEMP_MINIMUM)
        )

    @property
    def current_setting(self):
        """Get current scheduled setting (temp or state)"""
        if self._type == "Heating":
            return self.current_target_temperature
        if self._type == "OnOff":
            return self.current_state

    @property
    def current_state(self) -> str:
        """Get current scheduled state for on off device"""
        return self._schedule_data.get("CurrentState", TEXT_UNKNOWN)

    @property
    def id(self) -> int:
        """Get id of schedule"""
        return self._schedule_data.get("id")

    @property
    def name(self) -> str:
        """Get name of schedule"""
        return self._schedule_data.get("Name")

    @property
    def next_entry(self):
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
        return self._send_schedule(self._schedule_data, to_id)

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
            _LOGGER.debug(ex)
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
            _LOGGER.debug(ex)
            return False

    def set_schedule(self, schedule_data: dict) -> bool:
        """
        Set new schedule
        param scheduleData: json data respresenting a schedule
        return: boolen - true = successfully set, false = failed to set
        """
        return self._send_schedule(self._remove_schedule_elements(schedule_data))

    def set_schedule_from_file(self, schedule_file: str):
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
            _LOGGER.debug(ex)
            return False

    def set_schedule_from_yaml_file(self, schedule_file: str) -> bool:
        """
        Set schedule from file.
        param schedule_file: file of yaml data respresenting a schedule
        return: boolen - true = successfully set, false = failed to set
        """
        try:
            yaml = YAML()
            with open(schedule_file, "r") as file:
                y = yaml.load(file)
                self.set_schedule(self._convert_to_wiser_schedule(y))
                return True
        except Exception as ex:
            _LOGGER.debug(ex)
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
    def time(self) -> int:
        """Get the next entry time"""
        # TODO: convert to time
        return self._data.get("Time", 0)

    @property
    def setting(self):
        """Get the next entry setting - temp for heating, state for on/off devices"""
        if self._schedule_type == TEXT_HEATING:
            return self._data.get("DegreesC")
        if self._schedule_type == TEXT_ONOFF:
            return self._data.get("State")
        return None