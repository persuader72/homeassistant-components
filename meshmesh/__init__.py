import voluptuous as vol
import logging

import xmlrpc.client

from homeassistant.const import (EVENT_HOMEASSISTANT_STOP, CONF_NAME)
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity import Entity

from meshmesh.qtgui.transport import RequestsTransport

_LOGGER = logging.getLogger(__name__)

DOMAIN = 'meshmesh'

CONF_URL = 'url'
DEFAULT_URL = "http://localhost:8801/"
CONF_ADDRESS = 'address'
DEFAULT_ADDRESS = '0'

DEFAULT_ADC_MAX_VOLTS = 1.2
ESP_ADC_RESOLUTION = 1023.0

MESHMESH_EXCEPTION = None
MESHMESH_TX_FAILURE = None

DEVICE = None

ADC_PERCENTAGE = None

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_URL): cv.url,
    }),
}, extra=vol.ALLOW_EXTRA)

PLATFORM_SCHEMA = vol.Schema({
    vol.Required(CONF_NAME): cv.string,
    vol.Required(CONF_ADDRESS): cv.positive_int,
}, extra=vol.ALLOW_EXTRA)


def setup(hass, config):
    global DEVICE

    url = config[DOMAIN].get(CONF_URL, DEFAULT_URL)
    DEVICE = xmlrpc.client.ServerProxy(url, transport=RequestsTransport())

    """Your controller/hub specific code."""
    hass.bus.listen_once(EVENT_HOMEASSISTANT_STOP, close_xmlrpc)
    print(DOMAIN, 'setup', url)
    return True


def close_xmlrpc(*args):
    pass


class MeshMeshConfig(object):
    def __init__(self, config):
        self._config = config
        self._should_poll = config.get("poll", True)

    @property
    def name(self):
        return self._config["name"]

    @property
    def address(self):
        return self._config.get("address")

    @property
    def should_poll(self):
        return self._should_poll


class MeshMeshPinConfig(MeshMeshConfig):
    @property
    def pin(self):
        return self._config["pin"]


class MeshMeshAnalogInConfig(MeshMeshPinConfig):
    @property
    def max_voltage(self):
        """Return the voltage for ADC to report its highest value."""
        return float(self._config.get("max_volts", DEFAULT_ADC_MAX_VOLTS))


class MeshMeshAnalogIn(Entity):
    def __init__(self, hass, config):
        self._config = config
        self._value = None

    @property
    def name(self):
        return self._config.name

    @property
    def config(self):
        return self._config

    @property
    def should_poll(self):
        return self._config.should_poll

    @property
    def state(self):
        return self._value

    @property
    def unit_of_measurement(self):
        return "%"

    def update(self):
        try:
            print("MeshMeshAnalogIn.update %06X" % self._config.address)
            self._value = int(DEVICE.cmd_read_analog(self._config.address) / ESP_ADC_RESOLUTION * 1000.0) / 10.0
        except xmlrpc.client.Fault:
            _LOGGER.warning("MeshMeshLight.turn_on Transmission failure with device at addres: %08X", self._config.address)
        except ConnectionError:
            _LOGGER.warning("Connection error with meshmeshhub proxy server")


class MeshMeshAnalogOutConfig(MeshMeshPinConfig):
    @property
    def max_voltage(self):
        """Return the voltage for ADC to report its highest value."""
        return float(self._config.get("max_volts", DEFAULT_ADC_MAX_VOLTS))


class MeshMeshAnalogOut(Entity):
    def __init__(self, hass, config):
        self._config = config
        self._value = None


class MeshMeshDigitalInConfig(MeshMeshPinConfig):
    def __init__(self, config):
        super(MeshMeshDigitalInConfig, self).__init__(config)
        self._should_poll = config.get("poll", True)


class MeshMeshDigitalIn(Entity):
    def __init__(self, hass, config):
        self._config = config
        self._state = False

    @property
    def name(self):
        return self._config.name

    @property
    def config(self):
        return self._config

    @property
    def should_poll(self):
        return self._config.should_poll

    @property
    def is_on(self):
        return self._state

    def update(self):
        try:
            value = DEVICE.cmd_digital_in(self._config.pin, self._config.address)
            if value is None:
                _LOGGER.error("Null value returnd from device at address %08X", self._config.address)
                return
            self._state = value & self._config.pin != 0
        except xmlrpc.client.Fault:
            _LOGGER.warning("MeshMeshLight.turn_on Transmission failure with device at addres: %08X", self._config.address)
        except ConnectionError:
            _LOGGER.warning("Connection error with meshmeshhub proxy server")


class MeshMeshDigitalOutConfig(MeshMeshPinConfig):
    def __init__(self, config):
        super(MeshMeshDigitalOutConfig, self).__init__(config)
        self._should_poll = config.get("poll", True)


class MeshMeshDigitalOut(MeshMeshDigitalIn):
    def __init__(self, hass, config):
        super(MeshMeshDigitalOut, self).__init__(hass, config)

    def _set_state(self, state):
        try:
            DEVICE.cmd_digital_out(self._config.pin, self._config.pin if state else 0, self._config.address)
        except xmlrpc.client.Fault:
            _LOGGER.warning("Transmission failure when attempting to set pin on MeshMesh device at address: %08X", self._config.address)
        self._state = state
        if not self.should_poll:
            self.schedule_update_ha_state()

    def turn_on(self, **kwargs):
        self._set_state(True)

    def turn_off(self, **kwargs):
        self._set_state(False)
