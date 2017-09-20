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

TYPES = ['light', 'analog']

PLATFORM_SCHEMA = meshmesh.PLATFORM_SCHEMA.extend({
    vol.Required(CONF_TYPE): vol.In(TYPES),
    vol.Optional(CONF_MAX_VOLTS, default=DEFAULT_VOLTS): vol.Coerce(float),
})


def setup_platform(hass, config, add_devices, discovery_info=None):
    typ = config.get(CONF_TYPE)

    try:
        sensor_class, config_class = TYPE_CLASSES[typ]
    except KeyError:
        _LOGGER.exception("Unknown MeshMesh sensor type: %s", typ)
        return

    add_devices([sensor_class(hass, config_class(config))], True)
    return True


class MeshMeshLightSensor(Entity):
    """Representation of XBee Pro temperature sensor."""

    def __init__(self, hass, config):
        """Initialize the sensor."""
        self._config = config
        self._temp = None

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._config.name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._temp

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement the value is expressed in."""
        return TEMP_CELSIUS

    def update(self, *args):
        pass



# This must be below the classes to which it refers.
TYPE_CLASSES = {
    "light": (MeshMeshLightSensor, meshmesh.MeshMeshConfig),
    "analog": (meshmesh.MeshMeshAnalogIn, meshmesh.MeshMeshAnalogInConfig)
}
