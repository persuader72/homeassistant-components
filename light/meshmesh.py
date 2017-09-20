import voluptuous as vol
import logging

from homeassistant.helpers import config_validation as cv
from homeassistant.components.light import (
    Light, ATTR_BRIGHTNESS, ATTR_RGB_COLOR, SUPPORT_BRIGHTNESS, SUPPORT_RGB_COLOR)

from .. import meshmesh

_LOGGER = logging.getLogger(__name__)

CONF_ON_STATE = 'on_state'
CONF_ON_BRIGHTNESS = 'on_brightness'
DEFAULT_ON_STATE = True
DEFAULT_ON_BRIGHTNESS = 127

DEFAULT_CHANNEL = 255
BLUE_CHANNEL = 0
GREEN_CHANNEL = 1
RED_CHANNEL = 2
WHITE_CHANNEL = 3

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
        self._xy_color = (.5, .5)
        self._config = config

    def _set_rgb_color(self, red, green, blue):
        red = int(red/256.0*1024.0)
        green = int(green/256.0*1024.0)
        blue = int(blue/256.0*1024.0)
        white = 64

        try:
            meshmesh.DEVICE.set_analog_out(self._config.address, RED_CHANNEL, red)
            meshmesh.DEVICE.set_analog_out(self._config.address, GREEN_CHANNEL, green)
            meshmesh.DEVICE.set_analog_out(self._config.address, BLUE_CHANNEL, blue)
            meshmesh.DEVICE.set_analog_out(self._config.address, WHITE_CHANNEL, white)
        except meshmesh.MESHMESH_TX_FAILURE:
            _LOGGER.warning("MeshMeshLight.turn_on Transmission failure with device at addres: %08X", self._config.address)
        except meshmesh.MESHMESH_EXCEPTION:
            _LOGGER.warning("MeshMeshLight.turn_on Transmission failure with device at addres: %08X", self._config.address)

    def turn_on(self, **kwargs) -> None:
        print(kwargs)
        colors = kwargs[ATTR_RGB_COLOR] if ATTR_RGB_COLOR in kwargs else None
        if colors is not None:
            red, green, blue = colors
            self._set_rgb_color(red, green, blue)
        else:
            bright = kwargs[ATTR_BRIGHTNESS] if ATTR_BRIGHTNESS in kwargs else 128
            _LOGGER.debug("MeshMeshLight.turn_on set light %08X at brightness at %s color at %s", self._config.address, bright, color)
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
    def xy_color(self):
        """Return the XY color value [float, float]."""
        return self._xy_color

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
        return SUPPORT_BRIGHTNESS | SUPPORT_RGB_COLOR
