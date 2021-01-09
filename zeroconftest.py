#!/usr/bin/env python3

""" Example of browsing for a service.
The default is HTTP and HAP; use --find to search for all available services in the network
"""

import argparse
import logging
from time import sleep
from typing import cast

from zeroconf import IPVersion, ServiceBrowser, ServiceStateChange, Zeroconf, ZeroconfServiceTypes

foundHub = False

def on_service_state_change(
    zeroconf: Zeroconf, service_type: str, name: str, state_change: ServiceStateChange
) -> None:
    global foundHub
    print("Service %s of type %s state changed: %s" % (name, service_type, state_change))

    if state_change is ServiceStateChange.Added:
        info = zeroconf.get_service_info(service_type, name)
        print("Name: ", name)
        print("Info from zeroconf.get_service_info: %r" % (info))
        if info:
            addresses = ["%s:%d" % (addr, cast(int, info.port)) for addr in info.parsed_addresses()]
            print("  Addresses: %s" % ", ".join(addresses))
            print("  Weight: %d, priority: %d" % (info.weight, info.priority))
            print("  Server: %s" % (info.server,))
            if "WiserHeat" in info.server:
                print("Wiser Hub Found")
                print("Hub Name: %s" % (info.server))
                print("IP Address: %s" % (addresses[0].replace(":80","")))
                foundHub = True
            
        else:
            print("  No info")
        print('\n')


if __name__ == '__main__':
    zeroconf = Zeroconf()
    services = ["_http._tcp.local."]

    print("\nBrowsing %d service(s), press Ctrl-C to exit...\n" % len(services))
    browser = ServiceBrowser(zeroconf, services, handlers=[on_service_state_change])
    foundHub = False
    while True and not foundHub:
        sleep(0.1)
    zeroconf.close()