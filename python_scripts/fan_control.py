"""
Adjust the ceiling fan speed based on the temperature difference between the upstairs and downstairs thermostats.
"""
DEBUG = False
MESSAGE = True
entity_AWAY = 'binary_sensor.bayberry_away'
entity_UPSTAIRS_THERMOSTAT = 'sensor.upstairs_thermostat_temperature'
entity_DOWNSTAIRS_THERMOSTAT = 'sensor.downstairs_thermostat_temperature'
entity_FAN = 'fan.living_room_ceiling_fan'
entity_SUN = 'sun.sun'
entity_WEATHER = 'weather.dark_sky'
entity_B_BED = 'binary_sensor.sleepnumber_bill_bill_is_in_bed'
entity_C_BED = 'binary_sensor.sleepnumber_bill_cricket_is_in_bed'
FAN_LOW = 'low'
FAN_MEDIUM = 'medium'
FAN_HIGH = 'high'
FAN_OFF = 'off'
SUN_ELEV_HIGH = 60.00
SUN_ELEV_LOW = 25.00
SUN_AZ_HIGH = 180
WEATHER_SUNNY = ('sunny', 'partlycloudy')
HIGH_OUTDOOR_TEMP = 80
LOW_INDOOR_TEMP = 70

state_change = False
away_state = hass.states.get(entity_AWAY).state
fan_speed = hass.states.get(entity_FAN).attributes["speed"] or FAN_OFF
upstairs_temp = int(hass.states.get(entity_UPSTAIRS_THERMOSTAT).state)
downstairs_temp = int(hass.states.get(entity_DOWNSTAIRS_THERMOSTAT).state)
sun_elevation = float(hass.states.get(entity_SUN).attributes["elevation"])
sun_azimuth = float(hass.states.get(entity_SUN).attributes["azimuth"])
outdoor_temp = int(hass.states.get(entity_WEATHER).attributes["temperature"])
bill_asleep = hass.states.get(entity_B_BED).state
cricket_asleep = hass.states.get(entity_C_BED).state
weather = hass.states.get(entity_WEATHER).state
delta = abs(upstairs_temp - downstairs_temp)
new_speed = 'init'
fan_msg = 'init'

if DEBUG:
    debug_msg = 'Previous fan state: {}.'.format(fan_speed)
    hass.services.call('notify', 'slack_assistant', {"message": debug_msg})

# Normal adjustments
if delta <= 1:
    new_speed = FAN_OFF
elif delta == 2:
    new_speed = FAN_LOW
elif delta == 3:
    new_speed = FAN_MEDIUM
elif delta >= 4:
    new_speed = FAN_HIGH

# Special cases
if bill_asleep == 'on' and cricket_asleep == 'on':
    # Always use the fan at night
    pass
elif downstairs_temp <= LOW_INDOOR_TEMP and away_state == 'off':
    # Turn the fan off if too cool.
    new_speed = FAN_OFF
    fan_msg = 'It is too cool to use the fan.'
elif weather in WEATHER_SUNNY:
    # Set fan to high if direct sunlight
    if outdoor_temp > HIGH_OUTDOOR_TEMP:
        if SUN_ELEV_LOW < sun_elevation < SUN_ELEV_HIGH:
            if sun_azimuth > SUN_AZ_HIGH:
                new_speed = FAN_HIGH
                fan_msg = 'Setting fan to High based on sun position and {} weather.'.format(weather)


if fan_speed != new_speed and new_speed != 'init':
    # Adjust the speed.
    hass.services.call('fan', 'set_speed', {'entity_id': entity_FAN, 'speed': new_speed})
    state_change = True

    if DEBUG:
        debug_msg = 'Called speed: {}'.format(new_speed)
        hass.services.call('notify', 'slack_assistant', {"message": debug_msg})

if new_speed == 'init':
    new_speed = fan_speed

# Messaging
if state_change and MESSAGE:
    if fan_msg == 'init':
        fan_msg = 'Upstairs: {} Downstairs: {} Delta: {}.  Adjusting fan from {} to {}.'.format(upstairs_temp, downstairs_temp, delta, fan_speed, new_speed)

    logger.info(fan_msg)
    hass.services.call('notify', 'slack_assistant', {"message": fan_msg})

