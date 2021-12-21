from . import _LOGGER

from time import sleep
from typing import cast
from zeroconf import ServiceBrowser, ServiceStateChange, Zeroconf

class _WiserDiscoveredHub(object):

    def __init__(self, ip: str, hostname: str, name: str):
        self._ip = ip
        self._name = name
        self._hostname = hostname

    @property
    def ip(self) -> str:
        return self._ip

    @property
    def hostname(self) -> str:
        return self._hostname

    @property
    def name(self) -> str:
        return self._name
        

class WiserDiscovery(object):
    """
    Class to handle mDns discovery of a wiser hub on local network
    Use discover_hub() to return list of mDns responses.
    """

    def __init__(self):
        self._discovered_hubs = []

    def _zeroconf_on_service_state_change(
        self,
        zeroconf: Zeroconf,
        service_type: str,
        name: str,
        state_change: ServiceStateChange,
    ) -> None:
        """
        Look for Wiser Hub in discovered services and set IP and Name in
        global vars
        """
        if state_change is ServiceStateChange.Added:
            if "WiserHeat" in name:
                info = zeroconf.get_service_info(service_type, name)
                if info:
                    addresses = [
                        "%s:%d" % (addr, cast(int, info.port))
                        for addr in info.parsed_addresses()
                    ]
                    hub = _WiserDiscoveredHub(
                        ip = addresses[0].replace(":80", ""),
                        hostname = info.server.replace(".local.", ".local").lower(),
                        name = info.server.replace(".local.", ""),
                    )
                    _LOGGER.debug(
                        "Discovered Hub {} with IP Address {}".format(
                            info.server.replace(".local.", ""),
                            addresses[0].replace(":80", ""),
                        )
                    )
                    self._discovered_hubs.append(hub)

    def discover_hub(self, min_search_time: int = 2, max_search_time: int = 10):
        """
        Call zeroconf service browser to find Wiser hubs on the local network.
        param (optional) min_search_time: min seconds to wait for responses before returning
        param (optional) max_search_time: max seconds to wait for responses before returning
        return: list of discovered hubs
        """
        timeout = 0

        zeroconf = Zeroconf()
        services = ["_http._tcp.local."]
        ServiceBrowser(
            zeroconf, services, handlers=[self._zeroconf_on_service_state_change]
        )

        while (
            len(self._discovered_hubs) < 1 or timeout < min_search_time * 10
        ) and timeout < max_search_time * 10:
            sleep(0.1)
            timeout += 1

        zeroconf.close()
        return self._discovered_hubs