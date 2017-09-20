import voluptuous as vol
import logging

from homeassistant.helpers import config_validation as cv
from homeassistant.components.light import (Light, ATTR_BRIGHTNESS, SUPPORT_BRIGHTNESS)
from .. import meshmesh

_LOGGER = logging.getLogger(__name__)

CONF_ON_STATE = 'on_state'
CONF_ON_BRIGHTNESS = 'on_brightness'
DEFAULT_ON_STATE = True
DEFAULT_ON_BRIGHTNESS = 127
DEFAULT_CHANNEL = 255

PLATFORM_SCHEMA = meshmesh.PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_ON_STATE, default=DEFAULT_ON_STATE): cv.boolean,
    vol.Optional(CONF_ON_BRIGHTNESS, default=DEFAULT_ON_BRIGHTNESS): cv.positive_int,
})


def setup_platform(hass, config, add_devices, discovery_info=None):
    add_devices([MeshMeshLight(hass, MeshMeshLightConfig(config))])


class MeshMeshLightConfig(meshmesh.MeshMeshConfig):
    @property
    def on_state(self):
        return bool(self._config.get(CONF_ON_STATE, DEFAULT_ON_STATE))

    @property
    def on_state_brightness(self):
        return int(self._config.get(CONF_ON_BRIGHTNESS, DEFAULT_ON_BRIGHTNESS))


class MeshMeshLight(Light):

    def __init__(self, hass, config):
        self._optimistic = True
        self._state = config.on_state
        self._brightness = config.on_state_brightness
        self._config = config

    def turn_on(self, **kwargs) -> None:
        bright = kwargs[ATTR_BRIGHTNESS] if ATTR_BRIGHTNESS in kwargs else '128'
        _LOGGER.debug("MeshMeshLight.turn_on set light %08X at brightness at %s", self._config.address, bright)
        pwm = int(bright/256.0*1024.0)
        try:
            meshmesh.DEVICE.set_analog_out(self._config.address, DEFAULT_CHANNEL, pwm)
        except meshmesh.MESHMESH_TX_FAILURE:
            _LOGGER.warning("MeshMeshLight.turn_on Transmission failure with device at addres: %08X", self._config.address)
        except meshmesh.MESHMESH_EXCEPTION:
            _LOGGER.warning("MeshMeshLight.turn_on Transmission failure with device at addres: %08X", self._config.address)

        if self._optimistic:
            self._state = True
            self._brightness = bright
        self.schedule_update_ha_state()

    def turn_off(self, **kwargs) -> None:
        try:
            meshmesh.DEVICE.set_analog_out(self._config.address, DEFAULT_CHANNEL, 0)
        except meshmesh.MESHMESH_TX_FAILURE:
            _LOGGER.warning("MeshMeshLight.turn_off Transmission failure with device at address: %08X", self._config.address)
        except meshmesh.MESHMESH_EXCEPTION:
            _LOGGER.warning("MeshMeshLight.turn_off Transmission failure with device at address: %08X", self._config.address)

        if self._optimistic:
            self._state = False
            self._brightness = 0
        self.schedule_update_ha_state()

    @property
    def brightness(self):
        return self._brightness

    @property
    def should_poll(self):
        return False

    @property
    def name(self):
        return self._config.name

    @property
    def is_on(self):
        return self._state

    @property
    def supported_features(self):
        return SUPPORT_BRIGHTNESS
