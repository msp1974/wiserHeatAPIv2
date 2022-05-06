from . import _LOGGER

from .const import (
    REST_BACKOFF_FACTOR,
    REST_RETRIES,
    REST_TIMEOUT,
    WISERHUBDOMAIN,
    WISERHUBNETWORK,
    WISERHUBSCHEDULES,
    WiserUnitsEnum
)

from .exceptions import (
    WiserHubAuthenticationError,
    WiserHubConnectionError,
    WiserHubRESTError
)

import enum
import json
import logging
import re
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import urllib3

# Connection info class
class _WiserConnection(object):
    def __init(self):
        self.host = None
        self.secret = None
        self.units = WiserUnitsEnum.metric

# Enums
class WiserRestActionEnum(enum.Enum):
    GET = "GET"
    POST = "POST"
    PATCH = "PATCH"
    DELETE = "DELETE"

 
class _WiserRestController(object):
    """
    Class to handle getting data from and sending commands to a wiser hub
    """
    def __init__(self, wiser_connection:_WiserConnection):
        self._wiser_connection = wiser_connection
        
        # Settings for all API calls
        retries = Retry(
            total=REST_RETRIES, 
            backoff_factor=REST_BACKOFF_FACTOR, 
            status_forcelist=[429, 500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retries)
        self._requests_session = requests.Session()
        self._requests_session.mount("http://", adapter)
        self._requests_session.headers.update(
            {
                "SECRET": self._wiser_connection.secret,
                "Content-Type": "application/json;charset=UTF-8",
            }
        )
        logging.getLogger('urllib3.connectionpool').setLevel(logging.CRITICAL)
        logging.getLogger('urllib3.util.retry').setLevel(logging.CRITICAL)

    def _do_hub_action(self, action: WiserRestActionEnum, url: str, data: dict = None, raise_for_endpoint_error: bool = True):
        """
        Send patch update to hub and raise errors if fails
        param url: url of hub rest api endpoint
        param patchData: json object containing command and values to set
        return: boolean
        """
        try:
            if action == WiserRestActionEnum.GET:
                response = self._requests_session.get(
                    url.format(self._wiser_connection.host),
                    timeout=REST_TIMEOUT,
                )
            elif action == WiserRestActionEnum.PATCH:
                response = self._requests_session.patch(
                    url=url,
                    json=data,
                    timeout=REST_TIMEOUT,
                )
            elif action == WiserRestActionEnum.POST:
                response = self._requests_session.post(
                    url=url,
                    json=data,
                    timeout=REST_TIMEOUT,
                )
            elif action == WiserRestActionEnum.DELETE:
                response = self._requests_session.delete(
                    url=url,
                    json=data,
                    timeout=REST_TIMEOUT,
                )

            if not response.ok:
                self._process_nok_response(response, raise_for_endpoint_error)
            else:
                if action == WiserRestActionEnum.GET:
                    if len(response.content) > 0:
                        response = re.sub(rb'[^\x20-\x7F]+', b'', response.content)
                        return json.loads(response)
                else:
                    return True
            return {}

        except requests.exceptions.ConnectTimeout as ex:
            raise WiserHubConnectionError(
                f"Connection timeout trying to communicate with Wiser Hub {self._wiser_connection.host}.  Error is {ex}"
            )
        except requests.exceptions.ReadTimeout as ex:
            raise WiserHubConnectionError(
                f"Read timeout error trying to communicate with Wiser Hub {self._wiser_connection.host}.  Error is {ex}"
            )
        except requests.exceptions.ChunkedEncodingError as ex:
            raise WiserHubConnectionError(
                f"Chunked Encoding error trying to communicate with Wiser Hub {self._wiser_connection.host}.  Error is {ex}"
            )
        except requests.exceptions.ConnectionError as ex:
            raise WiserHubConnectionError(
                f"Connection error trying to communicate with Wiser Hub {self._wiser_connection.host}.  Error is {ex}"
            )
   
    def _process_nok_response(self, response, raise_for_endpoint_error: bool = True):
        if response.status_code == 401:
            raise WiserHubAuthenticationError(
                f"Error authenticating to Wiser Hub {self._wiser_connection.host}.  Check your secret key"
            )
        elif response.status_code == 404 and raise_for_endpoint_error:
            raise WiserHubRESTError(
                f"Rest endpoint not found on Wiser Hub {self._wiser_connection.host}"
            )
        elif response.status_code == 408:
            raise WiserHubConnectionError(
                f"Connection timed out trying to communicate with Wiser Hub {self._wiser_connection.host}"
            )
        elif raise_for_endpoint_error:
            raise WiserHubRESTError(
                f"Unknown error getting communicating with Wiser Hub {self._wiser_connection.host}.  Error code is: {response.status_code}"
            )

    def _get_hub_data(self, url:str, raise_for_endpoint_error: bool = True):
        """Get data from hub"""
        return self._do_hub_action(WiserRestActionEnum.GET ,url, raise_for_endpoint_error=raise_for_endpoint_error)

    def _send_command(self, url: str, command_data: dict, method: WiserRestActionEnum = WiserRestActionEnum.PATCH):
        """
        Send control command to hub and raise errors if fails
        param url: url of hub rest api endpoint
        param patchData: json object containing command and values to set
        return: boolean
        """
        url = WISERHUBDOMAIN.format(self._wiser_connection.host) + url
        _LOGGER.debug(
            "Sending command to url: {} with parameters {}".format(url, command_data)
        )
        
        if self._do_hub_action(method, url, command_data):
            return True

    def _do_schedule_action(self, action: WiserRestActionEnum, url: str, schedule_data: dict = None):
        """
        Perform schedule action to hub and raise errors if fails
        param url: url of hub rest api endpoint
        param patchData: json object containing schedule values to set
        return: boolean
        """
        url = WISERHUBSCHEDULES.format(self._wiser_connection.host) + url
        _LOGGER.debug(
            "Actioning schedule to url: {} with action {} and data {}".format(url, action.value, schedule_data)
        )
        return self._do_hub_action(action, url, schedule_data)

    def _send_schedule_command(self, action: str, schedule_data: dict, id: int = 0, schedule_type: str = None) -> bool:
        """
        Send schedule data to Wiser Hub
        param schedule_data: json schedule data
        param id: schedule id
        return: boolen - true = success, false = failed
        """
        if action == "UPDATE":
            result = self._do_schedule_action(
                WiserRestActionEnum.PATCH,
                "{}/{}".format(schedule_type, id),
                schedule_data,
            )

        elif action == "CREATE":
            result = self._do_schedule_action(
                WiserRestActionEnum.POST,
                "Assign",
                schedule_data,
            )

        elif action == "ASSIGN":
            result = self._do_schedule_action(
                WiserRestActionEnum.PATCH,
                "Assign",
                schedule_data,
            )
        
        elif action == "DELETE":
            result = self._do_schedule_action(
                WiserRestActionEnum.DELETE,
                "{}/{}".format(schedule_type, id),
                schedule_data,
            )
        return result


    