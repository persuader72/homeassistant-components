import voluptuous as vol

from homeassistant.components.switch import (SwitchDevice)
from .. import meshmesh

CONF_ON_STATE = 'on_state'
DEPENDENCIES = ['meshmesh']
STATES = ['high', 'low']

PLATFORM_SCHEMA = meshmesh.PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_ON_STATE): vol.In(STATES),
})


def setup_platform(hass, config, add_devices, discovery_info=None):
    add_devices([MeshMeshSwitch(hass, meshmesh.MeshMeshDigitalOutConfig(config))])


class MeshMeshSwitch(meshmesh.MeshMeshDigitalOut, SwitchDevice):
    pass