import voluptuous as vol

from homeassistant.components.binary_sensor import BinarySensorDevice
from .. import meshmesh

CONF_ON_STATE = 'on_state'

DEFAULT_ON_STATE = 'high'
DEPENDENCIES = ['meshmesh']

STATES = ['high', 'low']

PLATFORM_SCHEMA = meshmesh.PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_ON_STATE): vol.In(STATES),
})


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the ZigBee binary sensor platform."""
    add_devices(
        [MeshMeshBinarySensor(hass, meshmesh.MeshMeshDigitalInConfig(config))], True)


class MeshMeshBinarySensor(meshmesh.MeshMeshDigitalIn, BinarySensorDevice):
    """Use ZigBeeDigitalIn as binary sensor."""
    pass
