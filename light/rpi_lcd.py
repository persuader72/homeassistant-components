from os import path

from enocean.protocol.constants import PACKET

from homeassistant.components.light import Light, SUPPORT_BRIGHTNESS, ATTR_BRIGHTNESS

PATH_BL = "/sys/class/backlight/rpi_backlight/"
FILE_BL_POWER = "bl_power"
FILE_BL_BRIGHT = "brightness"
FILE_BL_CURR_BRIGHT = "actual_brightness"
FILE_BL_POWER_OFF = "1"
FILE_BL_POWER_ON = "0"

def setup_platform(hass, config, add_devices, discovery_info=None):
    add_devices(RpiLcdLight())


class RpiLcdLight(Light):
    def __init__(self):
        self._init = False
        self._state = False
        self._brightness = False

        if _sysclass_in(FILE_BL_POWER) != '':
            self._init = True

    @property
    def should_poll(self):
        return False

    @property
    def name(self):
        return "rpi_lcd"

    @property
    def brightness(self):
        return self._brightness

    @property
    def supported_features(self):
        return SUPPORT_BRIGHTNESS

    def turn_on(self, **kwargs):
        if ATTR_BRIGHTNESS in kwargs:
            val = kwargs[ATTR_BRIGHTNESS]
            _sysclass_out(FILE_BL_BRIGHT, val)
            _sysclass_out(FILE_BL_POWER, FILE_BL_POWER_ON)
        else:
            _sysclass_out(FILE_BL_POWER, FILE_BL_POWER_ON)
            pass

        self._state = True
        self.schedule_update_ha_state(True)

    def turn_off(self, **kwargs):
        _sysclass_out(FILE_BL_POWER, FILE_BL_POWER_OFF)
        self._state = False
        self.schedule_update_ha_state()

    @property
    def is_on(self):
        return self._state

    def update(self):
        self._state = _sysclass_in(FILE_BL_POWER) == FILE_BL_POWER_ON
        self._brightness = int(_sysclass_in(FILE_BL_CURR_BRIGHT))


def _sysclass_out(file, val):
    if path.exists(path.join(PATH_BL, file)):
        with open(path.join(PATH_BL, file), 'w') as f:
            f.write(val)
            f.write('\n')


def _sysclass_in(file):
    val = ''
    if path.exists(path.join(PATH_BL, file)):
        with open(path.join(PATH_BL, file), 'r') as f:
            val = f.read().strip()
    return val
