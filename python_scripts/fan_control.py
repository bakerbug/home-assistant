"""
Adjust the ceiling fan speed based on the temperature difference between the upstairs and downstairs thermostats.
"""

entity_UPSTAIRS_THERMOSTAT = 'sensor.upstairs_thermostat_temperature'
entity_DOWNSTAIRS_THERMOSTAT = 'sensor.downstairs_thermostat_temperature'
entity_FAN = 'THIS NAME NEEDS TO BE DISCOVERED ONCE SWITCH IS INSTALLED'
FAN_LOW = 1
FAN_MEDIUM = 2
FAN_HIGH = 3
FAN_OFF = 0



upstairs_temp = int(hass.states.get(entity_UPSTAIRS_THERMOSTAT).state)
downstairs_temp = int(hass.states.get(entity_DOWNSTAIRS_THERMOSTAT).state)
#fan_state = int(hass.states.get(entity_FAN).state)
fan_state = 0


delta = abs(upstairs_temp - downstairs_temp)
temp_msg = 'Upstairs: {} Downstairs: {} Delta: {}'.format(upstairs_temp, downstairs_temp, delta)
logger.info(temp_msg)
hass.services.call('notify', 'slack_assistant', {"message":  temp_msg})

if delta <= 1:
    fan_speed = FAN_OFF
elif delta == 2:
    fan_speed = FAN_LOW
elif delta == 3:
    fan_speed = FAN_MEDIUM
elif delta >= 4:
    fan_speed = FAN_HIGH

if fan_state != fan_speed:
    # Set new fan rate.
    fan_msg = 'HVAC delta of {} degrees.  Setting fan to {}'.format(delta, fan_speed)
    logger.info(fan_msg)
    hass.services.call('notify', 'slack_assistant', {"message": fan_msg})

