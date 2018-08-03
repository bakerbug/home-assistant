"""
Adjust the ceiling fan speed based on the temperature difference between the upstairs and downstairs thermostats.
"""

entity_UPSTAIRS_THERMOSTAT = 'sensor.upstairs_thermostat_temperature'
entity_DOWNSTAIRS_THERMOSTAT = 'sensor.downstairs_thermostat_temperature'
entity_FAN = 'fan.ceiling_fan'
FAN_LOW = 'low'
FAN_MEDIUM = 'medium'
FAN_HIGH = 'high'
FAN_OFF = 'off'
FAN_ON = 'on'

state_change = False
upstairs_temp = int(hass.states.get(entity_UPSTAIRS_THERMOSTAT).state)
downstairs_temp = int(hass.states.get(entity_DOWNSTAIRS_THERMOSTAT).state)
fan_state = hass.states.get(entity_FAN).state
fan_speed = hass.states.get(entity_FAN).attributes["speed"]
if fan_speed is None:
    fan_speed = FAN_OFF
delta = abs(upstairs_temp - downstairs_temp)
new_state = FAN_ON

if delta <= 1:
    new_speed = FAN_OFF
    new_state = FAN_OFF
elif delta == 2:
    new_speed = FAN_LOW
elif delta == 3:
    new_speed = FAN_MEDIUM
elif delta >= 4:
    new_speed = FAN_HIGH

if fan_state != new_state:
    # Toggle the fan.
    hass.services.call('fan', 'toggle', { 'entity_id': entity_FAN})
    state_change = True

if fan_speed != new_speed:
    # Adjust the speed.
    hass.services.call('fan', 'set_speed', { 'entity_id': entity_FAN, 'speed': new_speed})
    state_change = True

if state_change:
    fan_msg = 'Upstairs: {} Downstairs: {} Delta: {}.  Setting fan to {}'.format(upstairs_temp, downstairs_temp, delta, new_speed)
    logger.info(fan_msg)
    hass.services.call('notify', 'slack_assistant', {"message": fan_msg})

