import argparse
import configparser
import logging
import pathlib
import signal
import sys
import threading
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