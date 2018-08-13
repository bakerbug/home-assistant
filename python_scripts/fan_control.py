"""
Adjust the ceiling fan speed based on the temperature difference between the upstairs and downstairs thermostats.
"""

entity_UPSTAIRS_THERMOSTAT = 'sensor.upstairs_thermostat_temperature'
entity_DOWNSTAIRS_THERMOSTAT = 'sensor.downstairs_thermostat_temperature'
entity_FAN = 'fan.ceiling_fan'
entity_SUN = 'sun.sun'
FAN_LOW = 'low'
FAN_MEDIUM = 'medium'
FAN_HIGH = 'high'
FAN_OFF = 'off'
FAN_ON = 'on'
SUN_ELEV_HIGH = 60
SUN_ELEV_LOW = 20
SUN_AZ_HIGH = 180

state_change = False
fan_state = hass.states.get(entity_FAN).state
fan_speed = hass.states.get(entity_FAN).attributes["speed"] or FAN_OFF
upstairs_temp = int(hass.states.get(entity_UPSTAIRS_THERMOSTAT).state)
downstairs_temp = int(hass.states.get(entity_DOWNSTAIRS_THERMOSTAT).state)
sun_elevation = int(hass.states.get(entity_SUN).attributes["elevation"])
sun_azimuth = int(hass.states.get(entity_SUN).attributes["azimuth"])
delta = abs(upstairs_temp - downstairs_temp)
new_state = FAN_ON
new_speed = 'init'
fan_msg = 'init'

if delta <= 1:
    new_state = FAN_OFF
elif delta == 2:
    new_state = FAN_ON
    new_speed = FAN_LOW
elif delta == 3:
    new_state = FAN_ON
    new_speed = FAN_MEDIUM
elif delta >= 4:
    new_state = FAN_ON
    new_speed = FAN_HIGH

if SUN_ELEV_LOW < sun_elevation < SUN_AZ_HIGH:
    if sun_azimuth > SUN_AZ_HIGH:
        new_state = FAN_ON
        new_speed = FAN_HIGH
        fan_msg = 'Setting fan to High based on sun position.'

if fan_state != new_state:
    # Toggle the fan.
    fan_service = 'turn_' + new_state
    hass.services.call('fan', fan_service, {'entity_id': entity_FAN})
    state_change = True

if fan_speed != new_speed and new_speed != 'init':
    # Adjust the speed.
    hass.services.call('fan', 'set_speed', {'entity_id': entity_FAN, 'speed': new_speed})
    state_change = True

if new_speed == 'init':
    new_speed = fan_speed

if state_change:
    if fan_msg == 'init':
        if fan_state != new_state:
            fan_msg = 'Upstairs: {} Downstairs: {} Delta: {}.  Switching fan {} at {}.'.format(upstairs_temp, downstairs_temp, delta, new_state, new_speed)
        elif fan_speed != new_speed:
            fan_msg = 'Upstairs: {} Downstairs: {} Delta: {}.  Adjusting fan from {} to {}.'.format(upstairs_temp, downstairs_temp, delta, fan_speed, new_speed)

    logger.info(fan_msg)
    hass.services.call('notify', 'slack_assistant', {"message": fan_msg})

