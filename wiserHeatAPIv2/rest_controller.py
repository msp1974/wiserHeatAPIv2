from . import _LOGGER

from .const import (
    REST_TIMEOUT,
    WISERHUBDOMAIN,
    WISERHUBNETWORK,
    WISERHUBSCHEDULES,
    WiserUnitsEnum
)

from .exceptions import (
    WiserHubConnectionError,
    WiserHubAuthenticationError,
    WiserHubRESTError
)

from .exceptions import (
    WiserHubAuthenticationError,
    WiserHubConnectionError,
    WiserHubRESTError
)

import requests

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


    def _get_headers(self):
        """
        Define headers for wiser hub api calls
        return: json object
        """
        return {
            "SECRET": self._wiser_connection.secret,
            "Content-Type": "application/json;charset=UTF-8",
        }

    def _get_hub_data(self, url: str):
        """
        Read data from hub and raise errors if fails
        param url: url of hub rest api endpoint
        return: json object
        """
        url = url.format(self._wiser_connection.host)
        try:
            response = requests.get(
                url,
                headers=self._get_headers(),
                timeout=REST_TIMEOUT,
            )
            response.raise_for_status()

        except requests.exceptions.ConnectTimeout:
            raise WiserHubConnectionError(
                f"Connection timed out trying to update from Wiser Hub {self._wiser_connection.host}"
            )

        except requests.HTTPError as ex:
            if ex.response.status_code == 401:
                raise WiserHubAuthenticationError(
                    f"Error authenticating to Wiser Hub {self._wiser_connection.host}.  Check your secret key"
                )
            elif ex.response.status_code == 404:
                raise WiserHubRESTError(f"Rest endpoint not found on Wiser Hub {self._wiser_connection.host}")
            else:
                raise WiserHubRESTError(
                    f"Unknown error getting data from Wiser Hub {self._wiser_connection.host}.  Error code is: {ex.response.status_code}"
                )

        except requests.exceptions.ConnectionError:
            raise WiserHubConnectionError(
                f"Connection error trying to update from Wiser Hub {self._wiser_connection.host}"
            )

        except requests.exceptions.ChunkedEncodingError:
            raise WiserHubConnectionError(
                f"Chunked Encoding error trying to update from Wiser Hub {self._wiser_connection.host}"
            )

        return response.json()

    def _patch_hub_data(self, url: str, patch_data: dict):
        """
        Send patch update to hub and raise errors if fails
        param url: url of hub rest api endpoint
        param patchData: json object containing command and values to set
        return: boolean
        """
        try:
            response = requests.patch(
                url=url,
                headers=self._get_headers(),
                json=patch_data,
                timeout=REST_TIMEOUT,
            )
            # TODO: Improve error handling (maybe inc retry?)
            response.raise_for_status()

        except requests.exceptions.ConnectTimeout:
            raise WiserHubConnectionError(
                "Connection timed out trying to send command to Wiser Hub"
            )

        except requests.HTTPError as ex:
            if ex.response.status_code == 401:
                raise WiserHubAuthenticationError(
                    "Error authenticating to Wiser Hub.  Check your secret key"
                )
            elif ex.response.status_code == 404:
                raise WiserHubRESTError("Rest endpoint not found on Wiser Hub")
            else:
                raise WiserHubRESTError(
                    "Error setting {} , error {} {}".format(
                        patch_data, response.status_code, response.text
                    )
                )

        except requests.exceptions.ConnectionError:
            raise WiserHubConnectionError(
                "Connection error trying to send command to Wiser Hub"
            )

        except requests.exceptions.ChunkedEncodingError:
            raise WiserHubConnectionError(
                "Chunked Encoding error trying to send command to Wiser Hub"
            )

        return True

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


    