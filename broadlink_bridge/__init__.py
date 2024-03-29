import broadlink
import logging
import pkg_resources
from .util import *

NAME    = 'broadlink-bridge'
VERSION = pkg_resources.get_distribution(NAME).version
SERVER  = NAME + '/' + VERSION
LOGGER  = logging.getLogger(__name__)

class Registry:
    def __init__(self):
        self._device_types = {}
        self._devices = []
        self._devices_by_alias = {}
        self._commands = {}

    def add_device_type(self, type_id, implementation_class, device_name, manufacturer):
        self._device_types[type_id] = (implementation_class, device_name, manufacturer)

    def has_device_type(self, type_id):
        return type_id in self._device_types

    def get_device_type(self, type_id):
        return self._device_types[type_id]

    def add_manual_device(self, host, alias=None):
        return self._add_device(host, alias)

    def discover(self, timeout=None):
        if not timeout or timeout <= 0:
            LOGGER.info('Discovery disabled')
            return False
        
        LOGGER.info("Discovery: searching for devices for %s seconds...", timeout)
        devices = broadlink.discover(timeout=timeout)
        if not isinstance(devices, list):
            devices = [devices]
        for dev in devices:
            dev = self._add_device(dev)
        return True if self._devices else False

    def get_devices(self):
        return self._devices
    
    def find_device(self, id):
        LOGGER.debug('Finding device: %s...', id)
        device = self._devices_by_alias.get(id)
        if device:
            LOGGER.debug('Found device by alias: %s', device)
            return device
        elif id == 'default':
            if self._devices:
                device = self._devices[0]
                LOGGER.debug('Using first device: %s', device)
                return device
        else:
            mac = mac_format(id)
            for device in self._devices:
                if mac == device.mac or id == device.host or id in device.addresses:
                    LOGGER.debug('Found device by address: %s', device)
                    return device
            LOGGER.debug('Checking if device exists at address: %s', id)
            device = Device(id)
            if device.connect():
                LOGGER.debug('Found device %s, registering', device)
                self._add_device(device)
                return device
        LOGGER.debug('Device not found.')
        return None

    def set_command(self, command, data):
        if ' ' in command:
            raise ValueError('Commands cannot contain spaces: ' + command)
        LOGGER.info('Registering command: %s', command)
        self._commands[command] = ir_decode(data)[0]

    def get_commands(self):
        return self._commands.keys()
    
    def get_command(self, command):
        return self._commands.get(command)

    def _add_device(self, dev, alias=None):
        if not isinstance(dev, Device):
            dev = Device(dev)
        if not alias:
            alias = dev.host
        
        if alias not in self._devices_by_alias:
            LOGGER.info('Device: %s has alias %s', dev, alias)
            self._devices.append(dev)
            self._devices_by_alias[alias] = dev
            return dev
        else:
            LOGGER.info('Device: %s skipped, alias %s already exists', dev, alias)
            return None

class Device:
    def __init__(self, host=None):
        self._host = None
        self._dev = None
        self._mac = None
        self._addresses = None

        if isinstance(host, str):
            self._host = host
        elif isinstance(host, broadlink.device.Device):
            self._host = host.host[0]
        assert self._host

        self.connect()

    def connect(self):
        if self._dev:
            return True
        else:
            connected = False
            try:
                self._dev = broadlink.hello(host=self.host)
                if self._dev:
                    connected = self._dev.auth()
            except (socket.gaierror, socket.timeout):
                pass

            if connected and self._dev.get_type() == 'Unknown':
                type_id = self._dev.devtype
                connected = False
                self._dev = None
                
                LOGGER.warning('Device type %s unsupported by python-broadlink module', hex(type_id))
                if REGISTRY.has_device_type(type_id) and type_id not in broadlink.SUPPORTED_TYPES:
                    device_type = REGISTRY.get_device_type(type_id)
                    broadlink.SUPPORTED_TYPES[type_id] = device_type
                    LOGGER.warning('Trying configured device type %s: %s', type_id, device_type[2])
                    return self.connect()

            if self._dev and connected:
                LOGGER.info("Connected: %s", self._dev)
                self._mac = mac_format(self._dev.mac)
                self._addresses = get_ip_addresses(self._dev.host[0])
                return True
            else:
                self._dev = None
                self._mac = None
                self._addresses = None
        return False

    @property
    def host(self):
        return self._host

    @property
    def mac(self):
        if self.connect():
            return self._mac
        else:
            return '??-??-??-??-??-??'

    @property
    def addresses(self):
        if self.connect():
            return self._addresses
        else:
            return []

    def transmit(self, code, repeat=None):
        if not isinstance(code, str):
            code = code.decode('US-ASCII')

        (code, repeat) = ir_decode_multiply(code, repeat)
        command_code = REGISTRY.get_command(code)
        if command_code:
            code = command_code
        return self._transmit(code, repeat=repeat)

    def _transmit(self, code, repeat=None):
        (code, repeat) = ir_decode(code, repeat=repeat)
        LOGGER.debug('Transmitting to: %s (repeat: %s)', self, repeat)
        if self.connect():
            self._dev.send_data(code)
            return True
        else:
            return False

    def __str__(self):
        return self.mac + '@' + self.host

    def __repr__(self):
        return self.__str__()

REGISTRY = Registry()
