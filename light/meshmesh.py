import voluptuous as vol
import logging

from xmlrpc.client import Fault

from homeassistant.helpers import config_validation as cv
from homeassistant.components.light import (
    Light, ATTR_BRIGHTNESS, ATTR_RGB_COLOR, SUPPORT_BRIGHTNESS, SUPPORT_RGB_COLOR)

from .. import meshmesh

_LOGGER = logging.getLogger(__name__)

CONF_ON_STATE = 'on_state'
DEFAULT_ON_STATE = True

CONF_ON_BRIGHTNESS = 'on_brightness'
DEFAULT_ON_BRIGHTNESS = 224

CONF_MODE = "mode"
DEFAULT_MODE = "pwm"
MODES = ['pwm', 'pwmrgb', 'dali']

DEFAULT_CHANNEL = 255
BLUE_CHANNEL = 0
RED_CHANNEL = 1
GREEN_CHANNEL = 2
WHITE_CHANNEL = 3


PLATFORM_SCHEMA = meshmesh.PLATFORM_SCHEMA.extend({
    vol.Required(CONF_MODE): vol.In(MODES),
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

    @property
    def mode(self):
        return self._config.get(CONF_MODE, DEFAULT_MODE)


class MeshMeshLight(Light):
    def __init__(self, hass, config):
        self._optimistic = True
        self._state = config.on_state
        self._brightness = config.on_state_brightness
        self._mode = config.mode
        self._xy_color = (.5, .5)
        self._config = config

    def _set_brighness(self, bright):
        try:
            meshmesh.DEVICE.cmd_custom_light_set(0, 0, 0, bright, self._config.address)
        except Fault:
            _LOGGER.warning("MeshMeshLight._turn_pwm_on Transmission failure with device at addres: %08X", self._config.address)
        except ConnectionError:
            _LOGGER.warning("Connection error with meshmeshhub proxy server")

    def _set_rgb_color(self, red, green, blue):
        try:
            meshmesh.DEVICE.cmd_custom_light_set(red, green, blue, 0, self._config.address)
        except Fault:
            print(str(Fault))
            _LOGGER.warning("MeshMeshLight.turn_on Transmission failure with device at addres: %08X", self._config.address)
        except ConnectionError:
            _LOGGER.warning("Connection error with meshmeshhub proxy server")

    def _turn_dali_on(self, bright):
        _LOGGER.warning("_turn_dali_on bright %d", bright)
        try:
            meshmesh.DEVICE.cmd_dali_set_power(bright, self._config.address)
        except Fault:
            _LOGGER.warning("MeshMeshLight._turn_dali_on Transmission failure with device at addres: %08X", self._config.address)
        except ConnectionError:
            _LOGGER.warning("Connection error with meshmeshhub proxy server")

    def turn_on(self, **kwargs) -> None:
        bright = kwargs[ATTR_BRIGHTNESS] if ATTR_BRIGHTNESS in kwargs else None
        colors = kwargs[ATTR_RGB_COLOR] if ATTR_RGB_COLOR in kwargs else None
        _LOGGER.debug("MeshMeshLight.turn_on set light %08X at brightness at %s color at %s", self._config.address, bright, colors)
        if bright is None and colors is None:
            bright = DEFAULT_ON_BRIGHTNESS

        if self._mode == 'pwm' and bright is not None:
            self._set_brighness(bright)
        elif self._mode == 'dali' and bright is not None:
            self._turn_dali_on(bright)
        elif self._mode == 'pwmrgb':
            if colors is not None:
                red, green, blue = colors
                self._set_rgb_color(red, green, blue)
            elif bright is not None:
                self._set_brighness(bright)

        if self._optimistic:
            self._state = True
            self._brightness = bright

        self.schedule_update_ha_state()

    def turn_off(self, **kwargs) -> None:
        if self._mode == 'pwm':
            self._set_brighness(0)
        elif self._mode == 'pwmrgb':
            self._set_brighness(0)
        elif self._mode == 'dali':
            self._turn_dali_on(0)

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
        if self._mode == 'pwm' or self._mode == 'dali':
            return SUPPORT_BRIGHTNESS
        else:
            return SUPPORT_BRIGHTNESS | SUPPORT_RGB_COLOR
