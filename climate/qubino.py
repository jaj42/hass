from enum import Enum
from functools import partial

from homeassistant.components.climate import (ClimateDevice, SUPPORT_OPERATION_MODE)
from homeassistant.const import TEMP_CELSIUS

CONF_NAME = 'name'
CONF_ENTITY = 'entity_id'
CONF_HIDE = 'hide_parent'

class PWModes(Enum):
    Stop     = 1
    HorsGel  = 2
    Eco      = 3
    Confort2 = 4
    Confort1 = 5
    Confort  = 6

class PWState():
    opmodes = {PWModes.Stop     : 'Off',
               PWModes.HorsGel  : 'No Frost',
               PWModes.Eco      : 'Eco',
               PWModes.Confort2 : 'Confort -2°C',
               PWModes.Confort1 : 'Confort -1°C',
               PWModes.Confort  : 'Confort'}

    def __init__(self, state: PWModes):
        self._state = state
        self.reverse_opmodes = {value : key for key, value in self.opmodes.items()}

    @classmethod
    def from_dimmer(cls, dimperc):
        if dimperc <= 10:
            state = PWModes.Stop
        elif 10 < dimperc <= 20:
            state = PWModes.HorsGel
        elif 20 < dimperc <= 30:
            state = PWModes.Eco
        elif 30 < dimperc <= 40:
            state = PWModes.Confort2
        elif 40 < dimperc <= 50:
            state = PWModes.Confort1
        else:
            state = PWModes.Confort
        return cls(state)

    @property
    def dimvalue(self):
        stateint = self._state.value
        return (stateint * 10) - 5

    def __str__(self):
        return self.opmodes[self._state]

    def __repr__(self):
        return str(self._state)

def handle_event(source_entity_id, dest_entity, event):
    data = event.data
    if data['entity_id'] != source_entity_id:
        return
    newstate = data['new_state']
    if newstate.state == 'off':
        newpwstate = PWState(PWModes.Stop)
    else:
        attrs = newstate.attributes
        brightness = attrs['brightness']
        brightness_pct = int(100 * brightness / 255)
        newpwstate = PWState.from_dimmer(brightness_pct)
    dest_entity.set_operation_mode(str(newpwstate))

def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Demo climate devices."""

    dimmer_entity_id = config.get(CONF_ENTITY)
    entity_name = config.get(CONF_NAME)
    qubinoentity = QubinoPilotWire(entity_name, dimmer_entity_id)

#    s = hass.states.get(dimmer_entity_id)
#    print(s)

    event_handler = partial(handle_event, dimmer_entity_id, qubinoentity)
    hass.bus.listen('state_changed', event_handler)

    add_entities([qubinoentity])

class QubinoPilotWire(ClimateDevice):
    def __init__(self, name, dimmer_entity_id):
        """Initialize the climate device."""
        self._name = name
        self._dimmer_entity_id = dimmer_entity_id
        #self._support_flags = SUPPORT_OPERATION_MODE | SUPPORT_TARGET_TEMPERATURE
        self._support_flags = SUPPORT_OPERATION_MODE
        self._operation_list = {'Off'          : PWModes.Stop,
                                'No Frost'     : PWModes.HorsGel,
                                'Eco'          : PWModes.Eco,
                                'Confort -2°C' : PWModes.Confort2,
                                'Confort -1°C' : PWModes.Confort1,
                                'Confort'      : PWModes.Confort}
        self._current_operation = 'Confort'

    def set_operation_mode(self, operation_mode):
        """Set new operation mode."""
        pwstate =  self._operation_list[operation_mode]
        service_data = {'entity_id': self._dimmer_entity_id, 'brightness_pct': PWState(pwstate).dimvalue }
        try:
            self.hass.services.call('light', 'turn_on', service_data, False)
        except Exception as e:
            print(e)
            return
        self._current_operation = operation_mode
        self.schedule_update_ha_state()

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return self._support_flags

    @property
    def should_poll(self):
        """Return the polling state."""
        return False

    @property
    def name(self):
        """Return the name of the climate device."""
        return self._name

    @property
    def current_operation(self):
        """Return current operation mode."""
        return self._current_operation

    @property
    def operation_list(self):
        """Return the list of available operation modes."""
        return list(self._operation_list.keys())

    # This seems to be necessary for Climate
    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return TEMP_CELSIUS
