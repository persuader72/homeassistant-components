import voluptuous as vol
import logging
from serial import Serial, SerialException
from binascii import hexlify, unhexlify
from struct import unpack

from homeassistant.const import (EVENT_HOMEASSISTANT_STOP, CONF_DEVICE, CONF_NAME, CONF_PIN)
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity import Entity

#REQUIREMENTS = ['meshmesh==0.0.7']

_LOGGER = logging.getLogger(__name__)

DOMAIN = 'meshmesh'

CONF_ADDRESS = 'address'
CONF_BAUD = 'baud'

DEFAULT_DEVICE = '/dev/ttyUSB0'
DEFAULT_BAUD = 115200
DEFAULT_ADC_MAX_VOLTS = 1.2
ESP_ADC_RESOLUTION = 1023.0

MESHMESH_EXCEPTION = None
MESHMESH_TX_FAILURE = None

DEVICE = None

ADC_PERCENTAGE = None

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Optional(CONF_BAUD, default=DEFAULT_BAUD): cv.string,
        vol.Optional(CONF_DEVICE, default=DEFAULT_DEVICE): cv.string,
    }),
}, extra=vol.ALLOW_EXTRA)

PLATFORM_SCHEMA = vol.Schema({
    vol.Required(CONF_NAME): cv.string,
    vol.Optional(CONF_PIN): cv.positive_int,
    vol.Required(CONF_ADDRESS): cv.string,
}, extra=vol.ALLOW_EXTRA)


def setup(hass, config):
    global DEVICE
    global MESHMESH_EXCEPTION
    global MESHMESH_TX_FAILURE

    from meshmeshhub.meshmesh import MeshMesh
    from meshmeshhub.exceptions import (MeshMeshException, MeshMeshTxFailure)

    usb_device = config[DOMAIN].get(CONF_DEVICE, DEFAULT_DEVICE)
    baud = int(config[DOMAIN].get(CONF_BAUD, DEFAULT_BAUD))

    try:
        ser = Serial(usb_device, baudrate=baud)
    except SerialException as exc:
        print("SerialException %s", exc)
        return False

    DEVICE = MeshMesh(ser, director_present_callback=None)
    MESHMESH_EXCEPTION = MeshMeshException
    MESHMESH_TX_FAILURE = MeshMeshTxFailure

    """Your controller/hub specific code."""
    hass.bus.listen_once(EVENT_HOMEASSISTANT_STOP, close_serial_port)
    print(usb_device, baud)
    return True


def close_serial_port(*args):
    global DEVICE
    """Close the serial port we're using to communicate with the ZigBee."""
    DEVICE.mm.halt()


class MeshMeshConfig(object):
    def __init__(self, config):
        self._config = config
        self._should_poll = config.get("poll", True)

    @property
    def name(self):
        return self._config["name"]

    @property
    def address(self):
        address = self._config.get("address")
        if address is not None:
            address, = unpack('>I', unhexlify(address))
        return address

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
            self._value = int(DEVICE.read_analog_pin(self._config.address) / ESP_ADC_RESOLUTION * 1000.0) / 10.0
        except MESHMESH_TX_FAILURE:
            _LOGGER.warning("Transmission failure when attempting to get sample from MeshMesh device at address: %08X", self._config.address)
        except MESHMESH_EXCEPTION:
            _LOGGER.warning("Unable to get sample from MeshMesh device at address: %08X", self._config.address)


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
            value = DEVICE.cmd_digital_in(self._config.pin, serial=self._config.address, wait=True)
            if value is None:
                _LOGGER.error("Null value returnd from device at address %08X", self._config.address)
                return
            self._state = value & self._config.pin != 0
        except MESHMESH_TX_FAILURE:
            _LOGGER.warning("Transmission failure when attempting to get pin from MeshMesh device at address: %08X", self._config.address)
        except MESHMESH_EXCEPTION:
            _LOGGER.warning("Transmission failure when attempting to get pin from MeshMesh device at address: %08X", self._config.address)


class MeshMeshDigitalOutConfig(MeshMeshPinConfig):
    def __init__(self, config):
        super(MeshMeshDigitalOutConfig, self).__init__(config)
        self._should_poll = config.get("poll", True)


class MeshMeshDigitalOut(MeshMeshDigitalIn):
    def __init__(self, hass, config):
        super(MeshMeshDigitalOut, self).__init__(hass, config)

    def _set_state(self, state):
        try:
            frame = DEVICE.cmd_digital_out(self._config.pin, self._config.pin if state else 0, serial=self._config.address, wait=True)
        except MESHMESH_TX_FAILURE:
            _LOGGER.warning("Transmission failure when attempting to set output pin on ZigBee device at address: %08X", self._config.address)
            return
        except MESHMESH_EXCEPTION as exc:
            _LOGGER.exception("Unable to set digital pin on ZigBee device: %s", exc)
            return
        self._state = state
        if not self.should_poll:
            self.schedule_update_ha_state()

    def turn_on(self, **kwargs):
        self._set_state(True)

    def turn_off(self, **kwargs):
        self._set_state(False)

