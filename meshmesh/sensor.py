import logging

import voluptuous as vol

from xmlrpc.client import Fault

from .. import meshmesh
from homeassistant.const import TEMP_CELSIUS
from homeassistant.helpers.entity import Entity

_LOGGER = logging.getLogger(__name__)

CONF_TYPE = 'type'
CONF_MAX_VOLTS = 'max_volts'

DEFAULT_VOLTS = 1.2
DEPENDENCIES = ['meshmesh']

TYPES = ['analog', 'current', 'temperature', 'pressure', 'humidity', 'thermometer']
NAMES_TYPE = ['Analog', 'Current', 'Temperature', 'Pressure', 'Humidity', 'Temperature']

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
            return '°C'
        elif self._sens_type == 'humidity':
            return '%'
        elif self._sens_type == 'illumination':
            return 'lm'
        elif self._sens_type == 'lux':
            return 'lx'
        elif self._sens_type == 'pressure':
            return 'hPa'
        elif self._sens_type == 'thermometer':
            return '°C'

    def update(self):
        try:
            if self._sens_type == 'thermometer':
                self._value = meshmesh.DEVICE.cmd_custom_thermo_sample(0, self._config.address) / 10.0
            elif self._sens_type == 'current':
                self._value = meshmesh.DEVICE.cmd_custom_current_sample(self._config.address) / 4.0
            else:
                temp, press, humi = meshmesh.DEVICE.cmd_weather_data(self._config.address)
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
        except Fault:
            _LOGGER.warning("Transmission failure when attempting to get sample from MeshMesh device at address: %08X", self._config.address)
        except ConnectionError:
            _LOGGER.warning("Connection error with meshmeshhub proxy server")
