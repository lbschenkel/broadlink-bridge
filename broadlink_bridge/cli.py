import argparse
import configparser
import logging
import pathlib
import signal
import sys
import re
import threading
import broadlink
from . import LOGGER, NAME, REGISTRY, SERVER
from .http import httpd_start
from .lirc import lircd_start
from .mqtt import mqtt_connect

DEFAULTS = {
    'commands': {
    },
    'devices': {
    },
    'discovery': {
        'timeout': 5,
    },
    'http': {
        'port': '8780',
    },
    'lirc': {
        'port': '8765',
    },
    'mqtt': {
        'broker_url': '',
    }
}

def main():
    parser = argparse.ArgumentParser(
        description='Bridge to Broadlink devices',
    )
    parser.add_argument('config', metavar='CONFIG-FILE', nargs='?', help='path to configuration file')
    parser.add_argument('-d', '--debug', metavar='DEBUG', action='store_const', const=True, help='enable debug logging')
    args = parser.parse_args()

    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    console.setFormatter(logging.Formatter('%(asctime)s %(levelname)-8s %(message)s'))
    logger = logging.getLogger('')
    logger.addHandler(console)
    logger.setLevel(logging.INFO if not args.debug else logging.DEBUG)

    LOGGER.info('Starting %s...', SERVER)

    config = configparser.SafeConfigParser()
    config.read_dict(DEFAULTS)
    if args.config:
        LOGGER.info('Reading config file: %s', args.config)
        with open(args.config) as f:
            config.read_file(f)

    for item in config.items('commands'):
        command = item[0]
        payload = item[1]
        REGISTRY.set_command(command, payload)
    for item in config.items('device_types'):
        type_id = item[0].lower()
        definition = item[1]
        error_prefix = "Skipping invalid [device_types] entry '%s' in config" % type_id
        if not re.match('^0x[0-9a-f]{4}$', type_id):
            LOGGER.warning("%s (expected format 0x1234)", error_prefix)
            next
        int_type_id = int(type_id, 16)
        parts = re.split('\s*,\s*', definition)
        if len(parts) != 3:
            LOGGER.warning("%s: %s (expected 3 parts, comma-separated)", error_prefix, definition)
            next
        cls, name, manufacturer = parts
        try:
            implementation_class = getattr(broadlink, cls)
        except AttributeError:
            LOGGER.warning("%s: '%s' is not a valid python-broadlink class", error_prefix, cls)
            next
        LOGGER.info("Registering device type %s: %s", type_id, name)
        REGISTRY.add_device_type(int_type_id, implementation_class, name, manufacturer)
    for item in config.items('devices'):
        alias = item[0]
        url = item[1]
        REGISTRY.add_manual_device(url, alias)

    REGISTRY.discover(config.getint('discovery', 'timeout'))

    httpd_start(config.getint('http', 'port'))
    lircd_start(config.getint('lirc', 'port'))
    mqtt_connect(config.get('mqtt', 'broker_url'))

    quit = threading.Event()
    def quit_handler(signo, stack_frame):
        quit.set()
    signal.signal(signal.SIGINT, quit_handler)
    signal.signal(signal.SIGTERM, quit_handler)
    quit.wait()
    LOGGER.info('Exiting...')
