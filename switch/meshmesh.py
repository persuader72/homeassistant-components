import voluptuous as vol

from homeassistant.components.switch import (SwitchDevice)
from homeassistant.components.meshmesh import (MeshMeshDigitalOut, MeshMeshDigitalOutConfig, PLATFORM_SCHEMA)

CONF_ON_STATE = 'on_state'
DEPENDENCIES = ['meshmesh']
STATES = ['high', 'low']

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_ON_STATE): vol.In(STATES),
})


def setup_platform(hass, config, add_devices, discovery_info=None):
    add_devices([MeshMeshSwitch(hass, MeshMeshDigitalOutConfig(config))])


class MeshMeshSwitch(MeshMeshDigitalOut, SwitchDevice):
    pass