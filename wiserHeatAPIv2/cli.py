import argparse
import json
import logging
import pathlib
from sys import version_info

from . import __VERSION__

from .const import (
    WISERHUBDOMAIN,
    WISERHUBNETWORK,
    WISERHUBSCHEDULES
)
from .exceptions import (
    WiserHubAuthenticationError,
    WiserHubConnectionError,
    WiserHubRESTError
)
from wiserHeatAPIv2.rest_controller import _WiserConnection, _WiserRestController


def main_parser() -> argparse.ArgumentParser:
    logging.basicConfig(level=logging.ERROR)

    parser = argparse.ArgumentParser(description='A simple executable to use and test the wiserHeatAPIv2 library.')
    subparsers = parser.add_subparsers(dest='cmd')
    subparsers.required = True

    output_parser = subparsers.add_parser('output', description='Output json endpoints to files')
    output_parser.add_argument('-r','--raw', dest='raw', action='store_const', help='(optional) By default, sensitive data is anonomised.  Set this flag to output raw data without anonomisation from hub', const=True, default=False)
    _add_default_arguments(output_parser)
    output_parser.add_argument('type', help='What to output. Possible values are domain/network/schedule/all')
    output_parser.set_defaults(func=output_json)

    version_parser = subparsers.add_parser('version', description='Show api version')
    version_parser.set_defaults(func=show_version)

    return parser


def output_json(args) -> None:
    c = _WiserConnection()
    c.host = args.hostname
    c.secret = args.secret

    wiser_rest_controller = _WiserRestController(c)

    # Read data from hub
    try:
        if args.type == 'domain' or args.type == 'all':
            domain_data = wiser_rest_controller._get_hub_data(WISERHUBDOMAIN)
            log_response_to_file(domain_data, 'domain', args.raw)
        if args.type == 'network' or args.type == 'all':
            network_data = wiser_rest_controller._get_hub_data(WISERHUBNETWORK)
            log_response_to_file(network_data, 'network', args.raw)
        if args.type == 'schedule' or args.type == 'all':
            schedule_data = wiser_rest_controller._get_hub_data(WISERHUBSCHEDULES)
            log_response_to_file(schedule_data, 'schedule', args.raw)
    except WiserHubAuthenticationError:
        print("Unable to authenticate with your Wiser HeatHub.  Please check your secret key.")
    except WiserHubConnectionError:
        print("Unable to connect to your Wiser HeatHub.  Check your ip/hostname and that your hub is responding on the network.")
    except WiserHubRESTError:
        print("Your Wiser HeatHub returned an incorrectly formatted response.  Please check you are conncting to the correct device and try again.")
    except Exception as ex:
        print(f"Unknown error getting json data from your Wiser HeatHub.  Error is {ex}")

def show_version(args) -> None:
    print(f"API version is {__VERSION__}")


def _add_default_arguments(parser: argparse.ArgumentParser):
    """Add the default arguments username, password, region to the parser."""
    parser.add_argument('hostname', help='HeatHub IP or DNS name')
    parser.add_argument('secret', help='Heathub secret key')


def log_response_to_file(json_data: str, logfilename: str, raw: bool, log_responses: pathlib.Path = pathlib.Path.home()) -> None:
        """If a log path is set, log all resonses to a file."""
        if logfilename is None:
            return

        if raw:
            data = json.dumps(json_data, indent=2, sort_keys=False)
        else:
            data = json.dumps(anonymise_data(json_data), indent=2, sort_keys=False)

        output_path = log_responses / 'wiser_data/{}.json'.format(logfilename)

        output_path.parent.mkdir(exist_ok=True, parents=True); 
        with open(output_path, 'w', encoding='UTF-8') as logfile:
            logfile.write(data)

        print(f"{logfilename.title()} data written to {output_path}")

def anonymise_data(json_data: dict) -> dict:
    """Replace parts of the logfiles containing personal information."""

    replacements = {
        'Latitude': 30.4865, 
        'Longitude': 58.4892,
        'SerialNumber': 'ANON_SERIAL',
        'MacAddress': 'ANON_MAC',
        'HostName': 'WiserHeatXXXXXX',
        'MdnsHostname': 'WiserHeatXXXXXX',
        'IPv4Address': 'ANON_IP',
        'IPv4HostAddress': 'ANON_IP',
        'IPv4DefaultGateway': 'ANON_IP',
        'IPv4PrimaryDNS': 'ANON_IP',
        'IPv4SecondaryDNS': 'ANON_IP',
        'SSID': 'ANON_SSID',
        'DetectedAccessPoints': []
    }

    if isinstance(json_data, dict):
        for key, value in json_data.items():
            if isinstance(value, dict):
                json_data[key] = anonymise_data(value)
            elif isinstance(value, list):
                key_data = []
                for item in value:
                    key_data.append(anonymise_data(item))
                json_data[key] = key_data
            elif key in replacements:
                json_data[key] = replacements[key]
    return json_data


def main():
    """Main function."""
    parser = main_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()