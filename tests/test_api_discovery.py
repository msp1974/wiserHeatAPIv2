from wiserHeatAPIv2.discovery import WiserDiscovery

def discovery():
    try:
        w = WiserDiscovery()
        hubs = w.discover_hub()
        if hubs:
            for hub in hubs:
                print(f"Found hub {hub.name} with IP as {hub.ip} and Hostname as {hub.hostname}")

    except Exception as ex:
        print(ex)

discovery()