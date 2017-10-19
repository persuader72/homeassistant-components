import logging

import voluptuous as vol

from .. import meshmesh
from homeassistant.const import TEMP_CELSIUS
from homeassistant.helpers.entity import Entity

_LOGGER = logging.getLogger(__name__)

CONF_TYPE = 'type'
CONF_MAX_VOLTS = 'max_volts'

DEFAULT_VOLTS = 1.2
DEPENDENCIES = ['meshmesh']

TYPES = ['analog', 'temperature', 'pressure', 'humidity']
NAMES_TYPE = ['Analog', 'Temperature', 'Pressure', 'Humidity']

PLATFORM_SCHEMA = meshmesh.PLATFORM_SCHEMA.extend({
    vol.Required(CONF_TYPE): vol.In(TYPES),
    vol.Optional(CONF_MAX_VOLTS, default=DEFAULT_VOLTS): vol.Coerce(float),
})


def setup_platform(hass, config, add_devices, discovery_info=None):
    typ = config.get(CONF_TYPE)

    if typ == 'analog':
        add_devices([meshmesh.MeshMeshAnalogIn(hass, meshmesh.MeshMeshAnalogInConfig(config))], True)
    else:
        add_devices([MeshMeshSensor(typ, meshmesh.MeshMeshDigitalInConfig(config))], True)

    return True


class MeshMeshSensor(Entity):
    """Representation of XBee Pro temperature sensor."""

    def __init__(self, stype, config):
        self._sens_type = stype
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
        if self._sens_type == 'temperature':
            return TEMP_CELSIUS
        elif self._sens_type == 'humidity':
            return '%'
        elif self._sens_type == 'illumination':
            return 'lm'
        elif self._sens_type == 'lux':
            return 'lx'
        elif self._sens_type == 'pressure':
            return 'hPa'

    def update(self):
        try:
            temp, press, humi = meshmesh.DEVICE.cmd_weather_data(serial=self._config.address, wait=True)
            if self._sens_type == 'temperature':
                self._value = temp
            elif self._sens_type == 'humidity':
                self._value = humi
            elif self._sens_type == 'illumination':
                self._value = None
            elif self._sens_type == 'lux':
                self._value = None
            elif self._sens_type == 'pressure':
                self._value = press
        except meshmesh.MESHMESH_TX_FAILURE:
            _LOGGER.warning("Transmission failure when attempting to get sample from MeshMesh device at address: %08X", self._config.address)
        except meshmesh.MESHMESH_EXCEPTION:
            _LOGGER.warning("Unable to get sample from MeshMesh device at address: %08X", self._config.address)
