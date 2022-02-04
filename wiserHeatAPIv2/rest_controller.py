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


    def _get_hub_data(self, url: str):
        """
        Read data from hub and raise errors if fails
        param url: url of hub rest api endpoint
        return: json object
        """
        try:
            response = self._requests_session.get(
                url.format(self._wiser_connection.host),
                timeout=REST_TIMEOUT,
            )

            if not response.ok:
                self._process_nok_response(response)
                return {}
            else:
                if len(response.content) > 0:
                    response = re.sub(rb'[^\x20-\x7F]+', b'', response.content)
                    return json.loads(response)

            return {}

        except requests.exceptions.ConnectTimeout as ex:
            raise WiserHubConnectionError(
                f"Connection timeout trying to update from Wiser Hub {self._wiser_connection.host}.  Error is {ex}"
            )
        except requests.exceptions.ReadTimeout as ex:
            raise WiserHubConnectionError(
                f"Read timeout error trying to update from Wiser Hub {self._wiser_connection.host}.  Error is {ex}"
            )
        except requests.exceptions.ChunkedEncodingError as ex:
            raise WiserHubConnectionError(
                f"Chunked Encoding error trying to update from Wiser Hub {self._wiser_connection.host}.  Error is {ex}"
            )
        except requests.exceptions.ConnectionError as ex:
            raise WiserHubConnectionError(
                f"Connection error trying to update from Wiser Hub {self._wiser_connection.host}.  Error is {ex}"
            )
        


    def _patch_hub_data(self, url: str, patch_data: dict):
        """
        Send patch update to hub and raise errors if fails
        param url: url of hub rest api endpoint
        param patchData: json object containing command and values to set
        return: boolean
        """
        try:
            response = self._requests_session.patch(
                url=url,
                json=patch_data,
                timeout=REST_TIMEOUT,
            )

            if not response.ok:
                self._process_nok_response(response)
                return False
            else:
                return True

        except requests.exceptions.ConnectTimeout as ex:
            raise WiserHubConnectionError(
                f"Connection timeout trying to update from Wiser Hub {self._wiser_connection.host}.  Error is {ex}"
            )
        except requests.exceptions.ReadTimeout as ex:
            raise WiserHubConnectionError(
                f"Read timeout error trying to update from Wiser Hub {self._wiser_connection.host}.  Error is {ex}"
            )
        except requests.exceptions.ChunkedEncodingError as ex:
            raise WiserHubConnectionError(
                f"Chunked Encoding error trying to update from Wiser Hub {self._wiser_connection.host}.  Error is {ex}"
            )
        except requests.exceptions.ConnectionError as ex:
            raise WiserHubConnectionError(
                f"Connection error trying to update from Wiser Hub {self._wiser_connection.host}.  Error is {ex}"
            )


    def _process_nok_response(self, response):

            if response.status_code == 401:
                raise WiserHubAuthenticationError(
                    f"Error authenticating to Wiser Hub {self._wiser_connection.host}.  Check your secret key"
                )
            elif response.status_code == 404:
                raise WiserHubRESTError(
                    f"Rest endpoint not found on Wiser Hub {self._wiser_connection.host}"
                )
            elif response.status_code == 408:
                raise WiserHubConnectionError(
                    f"Connection timed out trying to update from Wiser Hub {self._wiser_connection.host}"
                )
            else:
                raise WiserHubRESTError(
                    f"Unknown error getting data from Wiser Hub {self._wiser_connection.host}.  Error code is: {response.status_code}"
                )

    def _send_command(self, url: str, command_data: dict):
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
        
        if self._patch_hub_data(url, command_data):
            return True


    def _send_schedule(self, url: str, schedule_data: dict):
        """
        Send schedule to hub and raise errors if fails
        param url: url of hub rest api endpoint
        param patchData: json object containing command and values to set
        return: boolean
        """
        url = url.format(self._wiser_connection.host)
        _LOGGER.debug(
            "Sending schedule to url: {} with data {}".format(url, schedule_data)
        )
        return self._patch_hub_data(url, schedule_data)


    