import voluptuous as vol
import logging

from xmlrpc.client import Fault

from homeassistant.components.binary_sensor import BinarySensorDevice
from .. import meshmesh

_LOGGER = logging.getLogger(__name__)

CONF_MODE = "mode"
DEFAULT_MODE = "pin"
MODES = ['pin', 'dali']

CONF_ON_STATE = 'on_state'

DEFAULT_ON_STATE = 'high'
DEPENDENCIES = ['meshmesh']

STATES = ['high', 'low']

PLATFORM_SCHEMA = meshmesh.PLATFORM_SCHEMA.extend({
    vol.Required(CONF_MODE): vol.In(MODES),
    vol.Optional(CONF_ON_STATE): vol.In(STATES),
})


def setup_platform(hass, config, add_devices, discovery_info=None):
    if config.get(CONF_MODE) == 'dali':
        add_devices([MeshMeshBinaryDaliStatus(hass, MeshMeshBinaryDaliStatusConfig(config))], True)
    else:
        add_devices([MeshMeshBinarySensor(hass, meshmesh.MeshMeshDigitalInConfig(config))], True)


class MeshMeshBinarySensor(meshmesh.MeshMeshDigitalIn, BinarySensorDevice):
    pass


class MeshMeshBinaryDaliStatusConfig(meshmesh.MeshMeshConfig):
    @property
    def mode(self):
        return self._config.get(CONF_MODE, DEFAULT_MODE)


class MeshMeshBinaryBase(BinarySensorDevice):
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


class MeshMeshBinaryDaliStatus(MeshMeshBinaryBase):
    def __init__(self, hass, config):
        super().__init__(hass, config)

    def update(self):
        try:
            value = meshmesh.DEVICE.cmd_dali_status(self._config.address)
            _LOGGER.debug("MeshMeshBinaryDaliStatus.update readed %d" % value)
            if value is None:
                _LOGGER.error("Null value returnd from device at address %08X", self._config.address)
                self._state = True
                return
            self._state = (value & 0x02) != 0
        except Fault:
            _LOGGER.warning("MeshMeshLight._turn_dali_on Transmission failure with device at addres: %08X", self._config.address)
            self._state = True
        except ConnectionError:
            _LOGGER.warning("Connection error with meshmeshhub proxy server")


class MeshMeshBinaryDaliPresence(MeshMeshBinaryBase):
    def __init__(self, hass, config):
        super().__init__(hass, config)

    def update(self):
        try:
            self._state = meshmesh.DEVICE.cmd_dali_presence(self._config.address)
            _LOGGER.debug("MeshMeshBinaryDaliPresence.update readed %d" % self._state)
         except Fault:
            _LOGGER.warning("MeshMeshLight._turn_dali_on Transmission failure with device at addres: %08X", self._config.address)
        except ConnectionError:
            _LOGGER.warning("Connection error with meshmeshhub proxy server")