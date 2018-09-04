"""
Notify when the garage doors open or close.  Turn on the lights if they open when dark.
"""

SUN_ELEV_HIGH = 15.00
entity_SUN = 'sun.sun'
early_LIGHTS = 'group.evening_early_lights'
late_LIGHTS = 'group.evening_lights'
sun_elevation = float(hass.states.get(entity_SUN).attributes["elevation"])
garage_id = data.get('entity')
time = hass.states.get('sensor.time').state
hour, minute = time.split(':')
hour = int(hour)


if garage_id is None:
    error_msg = 'Garage door triggered but entity_id is None.'
    hass.services.call('notify', 'slack_assistant', {"message": error_msg})
    exit()
else:
    label = hass.states.get(garage_id).attributes["friendly_name"]
    state = hass.states.get(garage_id).state
    garage_msg = '{} is {}.'.format(label, state)

if sun_elevation < SUN_ELEV_HIGH and state == 'open':
    if hour < 22:
        hass.services.call('switch', 'turn_on', {'entity_id': early_LIGHTS})
        hass.services.call('switch', 'turn_on', {'entity_id': late_LIGHTS})
        garage_msg = '{} is {}.  Turning on all lights.'.format(label, state)
    elif hour >= 22:
        hass.services.call('switch', 'turn_on', {'entity_id': late_LIGHTS})
        garage_msg = '{} is {}.  Turning on some lights.'.format(label, state)

hass.services.call('notify', 'slack_assistant', {"message": garage_msg})
