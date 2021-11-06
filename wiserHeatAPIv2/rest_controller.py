from .const import (
    WISERHUBDOMAIN,
    WiserUnitsEnum,
    REST_TIMEOUT
)

from .exceptions import (
    WiserHubConnectionError,
    WiserHubAuthenticationError,
    WiserHubRESTError
)
import logging
import requests

_LOGGER = logging.getLogger(__name__)

# Connection info class
class _WiserConnection:
    def __init(self):
        self.host = None
        self.secret = None
        self.hub_name = None
        self.units = WiserUnitsEnum.metric

class _WiserRestController:
    """
    Class to handle getting data from and sending commands to a wiser hub
    """
    def __init__(self, wiser_api_connection:_WiserConnection):
        self.wiser_api_connection = wiser_api_connection


    def _getHeaders(self):
        """
        Define headers for wiser hub api calls
        return: json object
        """
        return {
            "SECRET": self.wiser_api_connection.secret,
            "Content-Type": "application/json;charset=UTF-8",
        }

    def _getHubData(self, url: str):
        """
        Read data from hub and raise errors if fails
        param url: url of hub rest api endpoint
        return: json object
        """
        url = url.format(self.wiser_api_connection.host)
        try:
            response = requests.get(
                url,
                headers=self._getHeaders(),
                timeout=REST_TIMEOUT,
            )
            response.raise_for_status()

        except requests.exceptions.ConnectTimeout:
            raise WiserHubConnectionError(
                "Connection timed out trying to update from Wiser Hub"
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
                    "Unknown error getting data from Wiser Hub.  Error code is: {}".format(
                        ex.response.status_code
                    )
                )

        except requests.exceptions.ConnectionError:
            raise WiserHubConnectionError(
                "Connection error trying to update from Wiser Hub"
            )

        except requests.exceptions.ChunkedEncodingError:
            raise WiserHubConnectionError(
                "Chunked Encoding error trying to update from Wiser Hub"
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
                headers=self._getHeaders(),
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
        url = WISERHUBDOMAIN.format(self.wiser_api_connection.host) + url
        _LOGGER.info(
            "Sending command to url: {} with parameters {}".format(url, command_data)
        )
        return self._patch_hub_data(url, command_data)

    def _send_schedule(self, url: str, schedule_data: dict):
        """
        Send schedule to hub and raise errors if fails
        param url: url of hub rest api endpoint
        param patchData: json object containing command and values to set
        return: boolean
        """
        url = url.format(self.wiser_api_connection.host)
        _LOGGER.debug(
            "Sending schedule to url: {} with data {}".format(url, schedule_data)
        )
        return self._patch_hub_data(url, schedule_data)