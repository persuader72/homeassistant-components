import logging
import binascii
import voluptuous as vol
import homeassistant.helpers.config_validation as cv

from xmlrpc.client import Fault

from homeassistant.core import callback
from homeassistant.const import (STATE_OFF)
from homeassistant.components.climate import (ClimateDevice, PLATFORM_SCHEMA)
from homeassistant.components.climate.const import (STATE_DRY, STATE_HEAT, STATE_COOL, STATE_AUTO, ATTR_OPERATION_MODE, SUPPORT_OPERATION_MODE, SUPPORT_TARGET_TEMPERATURE, SUPPORT_FAN_MODE, SUPPORT_ON_OFF)
from homeassistant.const import (ATTR_UNIT_OF_MEASUREMENT, ATTR_TEMPERATURE, CONF_NAME, CONF_HOST, CONF_MAC, CONF_TIMEOUT, CONF_CUSTOMIZE)
from homeassistant.helpers.event import (async_track_state_change)
from homeassistant.helpers.restore_state import RestoreEntity

REQUIREMENTS = ['meshmesh_hub']

from .. import meshmesh

_LOGGER = logging.getLogger(__name__)

VERSION = '1.0.0'

SUPPORT_FLAGS = SUPPORT_ON_OFF | SUPPORT_TARGET_TEMPERATURE | SUPPORT_OPERATION_MODE | SUPPORT_FAN_MODE

CONF_MIN_TEMP = 'min_temp'
CONF_MAX_TEMP = 'max_temp'
CONF_TARGET_TEMP = 'target_temp'
CONF_TARGET_TEMP_STEP = 'target_temp_step'
CONF_TEMP_SENSOR = 'temp_sensor'
CONF_OPERATIONS = 'operations'
CONF_FAN_MODES = 'fan_modes'
CONF_DEFAULT_OPERATION = 'default_operation'
CONF_DEFAULT_FAN_MODE = 'default_fan_mode'

DEFAULT_TIMEOUT = 10
DEFAULT_MIN_TEMP = 16
DEFAULT_MAX_TEMP = 30
DEFAULT_TARGET_TEMP = 20
DEFAULT_TARGET_TEMP_STEP = 1
DEFAULT_OPERATION_LIST = [STATE_OFF, "", STATE_AUTO, STATE_HEAT, STATE_COOL, STATE_DRY]
DEFAULT_FAN_MODE_LIST = ['low', 'mid', 'high', 'auto']
DEFAULT_OPERATION = STATE_AUTO
DEFAULT_FAN_MODE = 'auto'

CUSTOMIZE_SCHEMA = vol.Schema({
    vol.Optional(CONF_OPERATIONS): vol.All(cv.ensure_list, [cv.string]),
    vol.Optional(CONF_FAN_MODES): vol.All(cv.ensure_list, [cv.string])
})

PLATFORM_SCHEMA = meshmesh.PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_TIMEOUT, default=DEFAULT_TIMEOUT): cv.positive_int,
    vol.Optional(CONF_MIN_TEMP, default=DEFAULT_MIN_TEMP): vol.Coerce(float),
    vol.Optional(CONF_MAX_TEMP, default=DEFAULT_MAX_TEMP): vol.Coerce(float),
    vol.Optional(CONF_TARGET_TEMP, default=DEFAULT_TARGET_TEMP): vol.Coerce(float),
    vol.Optional(CONF_TARGET_TEMP_STEP, default=DEFAULT_TARGET_TEMP_STEP): vol.Coerce(float),
    vol.Optional(CONF_TEMP_SENSOR): cv.entity_id,
    vol.Optional(CONF_CUSTOMIZE, default={}): CUSTOMIZE_SCHEMA,
    vol.Optional(CONF_DEFAULT_OPERATION, default=DEFAULT_OPERATION): cv.string,
    vol.Optional(CONF_DEFAULT_FAN_MODE, default=DEFAULT_FAN_MODE): cv.string,
})


async def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    min_temp = config.get(CONF_MIN_TEMP)
    max_temp = config.get(CONF_MAX_TEMP)
    target_temp = config.get(CONF_TARGET_TEMP)
    target_temp_step = config.get(CONF_TARGET_TEMP_STEP)
    operation_list = config.get(CONF_CUSTOMIZE).get(CONF_OPERATIONS, []) or DEFAULT_OPERATION_LIST
    fan_list = config.get(CONF_CUSTOMIZE).get(CONF_FAN_MODES, []) or DEFAULT_FAN_MODE_LIST
    default_fan_mode = config.get(CONF_DEFAULT_FAN_MODE)

    async_add_devices([
        MeshMeshClimate(hass, MeshMeshClimateConfig(config), min_temp, max_temp, target_temp, target_temp_step,
                        operation_list, fan_list, default_fan_mode)
    ])


class MeshMeshClimateConfig(meshmesh.MeshMeshConfig):
    @property
    def def_mode(self):
        return self._config.get(CONF_DEFAULT_OPERATION, DEFAULT_OPERATION)

    @property
    def temp_sensor(self):
        return self._config.get(CONF_TEMP_SENSOR, None)


class MeshMeshClimate(ClimateDevice, RestoreEntity):

    def __init__(self, hass, config, min_temp, max_temp, target_temp, target_temp_step, operation_list, fan_list,
                 default_fan_mode):

        """Initialize the Broadlink IR Climate device."""
        self.hass = hass
        self._name = config.name
        self._config = config

        self._is_on = False
        self._min_temp = min_temp
        self._max_temp = max_temp
        self._target_temperature = target_temp
        self._target_temperature_step = target_temp_step
        self._unit_of_measurement = hass.config.units.temperature_unit

        self._current_temperature = 0
        self._current_operation = self._config.def_mode
        self._current_fan_mode = default_fan_mode

        self._operation_list = operation_list
        self._fan_list = fan_list

        self._default_operation_from_idle = self._config.def_mode

        if self._config.temp_sensor:
            async_track_state_change(hass, self._config.temp_sensor, self._async_temp_sensor_changed)
            sensor_state = hass.states.get(self._config.temp_sensor)
            if sensor_state:
                _LOGGER.warning("MeshMeshClimate.__init__: state:%d", sensor_state)
                self._async_update_current_temp(sensor_state)

    def _set_state(self):
        try:
            mode = DEFAULT_OPERATION_LIST.index(self.current_operation)
            if self.is_on:
                mode |= 0x80
            temp = self.target_temperature
            _LOGGER.warning("MeshMeshClimate._set_state: mode:%d temp:%d", mode, temp)
            meshmesh.DEVICE.cmd_clima_set_ac_state(int(mode), int(temp), self._config.address)
        except Fault as e:
            _LOGGER.warning("MeshMeshClimate._set_state: Transmission failure with device at addres: %08X",
                            self._config.address)
            _LOGGER.warning("MeshMeshClimate._set_state: %s", str(e))
        except ConnectionError:
            _LOGGER.warning("MeshMeshClimate._set_state: Connection error with meshmeshhub proxy server")

    async def _async_temp_sensor_changed(self, entity_id, old_state, new_state):
        """Handle temperature changes."""
        if new_state is None:
            return

        self._async_update_current_temp(new_state)
        await self.async_update_ha_state()

    @callback
    def _async_update_current_temp(self, state):
        """Update thermostat with latest state from sensor."""
        unit = state.attributes.get(ATTR_UNIT_OF_MEASUREMENT)

        try:
            _state = state.state
            if self.represents_float(_state):
                #self._current_temperature = self.hass.config.units.temperature(float(_state), unit)
                self._current_temperature = float(_state)
        except ValueError as ex:
            _LOGGER.error('Unable to update from sensor: %s', ex)

    def represents_float(self, s):
        try:
            float(s)
            return True
        except ValueError:
            return False

    @property
    def should_poll(self):
        """Return the polling state."""
        return False

    @property
    def name(self):
        """Return the name of the climate device."""
        return self._name

    @property
    def is_on(self):
        """Return true if on."""
        return self._is_on

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return self._unit_of_measurement

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self._current_temperature

    @property
    def min_temp(self):
        """Return the polling state."""
        return self._min_temp

    @property
    def max_temp(self):
        """Return the polling state."""
        return self._max_temp

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._target_temperature

    @property
    def target_temperature_step(self):
        """Return the supported step of target temperature."""
        return self._target_temperature_step

    @property
    def current_operation(self):
        """Return current operation ie. heat, cool, idle."""
        return self._current_operation

    @property
    def operation_list(self):
        """Return the list of available operation modes."""
        return self._operation_list

    @property
    def current_fan_mode(self):
        """Return the fan setting."""
        return self._current_fan_mode

    @property
    def fan_list(self):
        """Return the list of available fan modes."""
        return self._fan_list

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return SUPPORT_FLAGS

    def turn_on(self):
        """Turn device on."""
        self._is_on = True
        self._set_state()

    def turn_off(self):
        """Turn device off."""
        self._is_on = False
        self._set_state()

    def set_temperature(self, **kwargs):
        """Set new target temperatures."""
        if kwargs.get(ATTR_TEMPERATURE) is not None:
            self._target_temperature = kwargs.get(ATTR_TEMPERATURE)

            if not (self._current_operation.lower() == 'off' or self._current_operation.lower() == 'idle'):
                self._set_state()
            elif self._default_operation_from_idle is not None:
                self.set_operation_mode(self._default_operation_from_idle)

            self.schedule_update_ha_state()

    def set_fan_mode(self, fan):
        """Set new target temperature."""
        self._current_fan_mode = fan

        if not (self._current_operation.lower() == 'off' or self._current_operation.lower() == 'idle'):
            self._set_state()

        self.schedule_update_ha_state()

    def set_operation_mode(self, operation_mode):
        """Set new target temperature."""
        self._current_operation = operation_mode

        self._set_state()
        self.schedule_update_ha_state()

    async def async_added_to_hass(self):
        """Run when entity about to be added."""
        await super().async_added_to_hass()

        last_state = await self.async_get_last_state()

        if last_state is not None:
            self._target_temperature = last_state.attributes['temperature']
            self._current_operation = last_state.attributes['operation_mode']
            self._current_fan_mode = last_state.attributes['fan_mode']
