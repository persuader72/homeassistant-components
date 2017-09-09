import logging
import time

import voluptuous as vol

from homeassistant.components.light import ATTR_BRIGHTNESS, SUPPORT_BRIGHTNESS, Light, turn_on, turn_off
from homeassistant.const import EVENT_HOMEASSISTANT_STOP, EVENT_HOMEASSISTANT_START
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.event import track_state_change

_LOGGER = logging.getLogger(__name__)

CONF_NAME = 'name'
CONF_LIGHT_ID = 'light_id'
CONF_SENSOR_ID = 'sensor_id'
DEFAULT_NAME = 'smartlight'
DEFAULT_LIGHT_ID = None
DEFAULT_SENSOR_ID = None
DEFAULT_ON_BRIGHTNESS = 128

CONFIG_SCHEMA = vol.Schema({
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Required(CONF_LIGHT_ID): cv.string,
    vol.Required(CONF_SENSOR_ID): cv.string,
}, extra=vol.ALLOW_EXTRA)


def setup_platform(hass, config, add_devices, discovery_info=None):
    add_devices([SmartLight(hass, config)])
    return True


class SmartLight(Light):
    def __init__(self, hass, config):
        self._hass = hass
        self._name = config.get(CONF_NAME, DEFAULT_NAME)
        self._light_id = config.get(CONF_LIGHT_ID, DEFAULT_LIGHT_ID)
        self._sensor_id = config.get(CONF_SENSOR_ID, DEFAULT_SENSOR_ID)
        self._state = False
        self._brightness = 0

        self.sensor_last_state = None
        self.sensor_target = 0
        self.light_delta_brightness = 0
        self.light_target_brightness = 0
        self.light_current_brightness = 0
        self.pid_const = (0.65, 0.01, 0.001, 15.0)
        self.pid_prev_error = None
        self.pid_prev_integral = None
        self.pid_prev_time = None
        self.time_interval_remove = None
        self.events_counter = 0

        """Your controller/hub specific code."""
        hass.bus.listen_once(EVENT_HOMEASSISTANT_START, self.homeassistant_start_event)

    @property
    def name(self):
        return self._name

    @property
    def brightness(self):
        return self._brightness

    @property
    def is_on(self):
        return self._state

    @property
    def supported_features(self):
        return SUPPORT_BRIGHTNESS

    def turn_on(self, **kwargs):
        self._state = True
        self._brightness = kwargs.get(ATTR_BRIGHTNESS, DEFAULT_ON_BRIGHTNESS)
        self.set_lux(int(self._brightness/255*100))

    def turn_off(self, **kwargs):
        self._state = False
        self._brightness = 0
        self.set_lux(0)

    def update(self):
        pass

    def homeassistant_start_event(self, *args):
        _LOGGER.debug("SmartLight.homeassistant_start_event")

        if self._hass.states.get(self._light_id) is None:
            _LOGGER.error("Light id %s could not be found in state machine", self._light_id)
            self._light_id = None

        if self._hass.states.get(self._sensor_id) is None:
            _LOGGER.error("Sensor id %s could not be found in state machine", self._sensor_id)
            self._sensor_id = None

        if self._sensor_id is not None and self._light_id is not None:
            track_state_change(self._hass, (self._sensor_id, 'sensor.test_sensor'), self.state_changed_listener, '*', '*')

    def state_changed_listener(self, entity_id, old_state, new_state):
        if self._sensor_id == entity_id:
            try:
                self.sensor_last_state = float(new_state.state)
            except ValueError:
                return

            # Update sensor data only if light is ON
            if self._state:
                _LOGGER.debug("SmartLight.state_changed_listener lux:%f target:%f", self.sensor_last_state, self.sensor_target)
                self.apply_pid()
                if self.light_target_brightness > 0:
                    turn_on(self._hass, self._light_id, brightness_pct=self.light_target_brightness)
                else:
                    turn_off(self._hass, self._light_id)

    def lux_to_brigthness(self, lux):
        return int(lux)

    def apply_pid(self):
        curr_time = time.time()
        error = self.sensor_target - self.sensor_last_state

        if self.pid_prev_time is not None:
            ts = curr_time - self.pid_prev_time
            feedfw = self.lux_to_brigthness(self.sensor_target)

            # PID constants
            kp, ki, kd, imax = self.pid_const
            # P term
            pid_p = error * kp
            # I term
            pid_i = self.pid_prev_integral + (error + self.pid_prev_error) / 2.0 * ts * kd if self.pid_prev_integral is not None else 0
            # I term Anti-windup
            if pid_i > 0:
                pid_i = pid_i if pid_i < imax else imax
            else:
                pid_i = pid_i if pid_i > -imax else -imax
            # D term
            pid_d = (error - self.pid_prev_error) / ts * ki if self.pid_prev_error is not None else 0
            # Calc PID output
            self.light_target_brightness = feedfw + pid_p + pid_i + pid_d
            # Constrain to 0 - 100 values
            self.light_target_brightness = min(100.0, max(0.0, self.light_target_brightness))

            _LOGGER.debug("SimpleLight.apply_pid FF:%f P:%f I:%f D:%f", feedfw, pid_p, pid_i, pid_d)
            _LOGGER.debug("SimpleLight.apply_pid target:%f error:%f output:%f", self.sensor_target, error, self.light_target_brightness)

            self.pid_prev_integral = pid_i

        self.pid_prev_error = error
        self.pid_prev_time = curr_time

    def reset_pid(self):
        self.pid_prev_time = None
        self.pid_prev_error = None
        self.pid_prev_integral = None

    def set_lux(self, target):
        # Read the lux target from service arguments
        self.sensor_target = target
        # Target to feedforward
        self.light_target_brightness = self.lux_to_brigthness(self.sensor_target)
        # Reset PID integral
        self.reset_pid()
        #  if brightness is 0 turn_off light set brightness otherwise
        if self.light_target_brightness > 0:
            turn_on(self._hass, self._light_id, brightness_pct=self.light_target_brightness)
        else:
            turn_off(self._hass, self._light_id)

        _LOGGER.debug("SimpleLight.set_lux called with %d lux => %d bright", self.sensor_target, self.light_target_brightness)
