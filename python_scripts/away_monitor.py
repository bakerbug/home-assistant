"""
Enables or disables automations based on away status.
"""

SEND_MSG = True
SUN_ELEV_HIGH = 15.00

entity_SUN = 'sun.sun'
all_LIGHTS = 'group.all_indoor_lights'
early_LIGHTS = 'group.evening_early_lights'
late_LIGHTS = 'group.evening_lights'
away_on_tuple = ('automation.hvac_balancing', 'automation.lights_off_when_away', 'automation.lights_on_when_away')
away_off_tuple = ('automation.lights_on_at_early_sunset', 'automation.lights_on_at_sunset', 'automation.lights_on_for_weekday_mornings')
home_on_tuple = ('automation.lights_on_at_early_sunset', 'automation.lights_on_at_sunset', 'automation.lights_on_for_weekday_mornings')
home_off_tuple = ('automation.lights_off_when_away', 'automation.lights_on_when_away')
nest_away = hass.states.get('binary_sensor.bayberry_away').state
bill_phone = hass.states.get('device_tracker.bill_cell').state
cricket_phone = hass.states.get('device_tracker.cricket_cell').state
person_id = data.get('entity')
person_label = hass.states.get(person_id).attributes["friendly_name"]
person_state = hass.states.get(person_id).state
sun_elevation = float(hass.states.get(entity_SUN).attributes["elevation"])
time = hass.states.get('sensor.time').state
hour, minute = time.split(':')
hour = int(hour)
light_msg = ''
house_msg = ''


if bill_phone == 'home' or cricket_phone == 'home':
    house_is_vacant = False
else:
    house_is_vacant = True
    house_msg = '  The house is empty.'

if house_is_vacant:
    for automation in away_on_tuple:
        hass.services.call('automation', 'turn_on', {'entity_id': automation})
    for automation in away_off_tuple:
        hass.services.call('automation', 'turn_off', {'entity_id': automation})

    hass.services.call('switch', 'turn_off', {'entity_id': all_LIGHTS})

elif person_state == 'home':
    # Somebody is home
    if sun_elevation < SUN_ELEV_HIGH:
        if 7 < hour < 22:
            hass.services.call('switch', 'turn_on', {'entity_id': early_LIGHTS})
            hass.services.call('switch', 'turn_on', {'entity_id': late_LIGHTS})
            light_msg = '  Turning on all lights.'
        elif 7 >= hour or hour >= 22:
            hass.services.call('switch', 'turn_on', {'entity_id': late_LIGHTS})
            light_msg = '  Turning on some lights.'

    for automation in home_on_tuple:
        hass.services.call('automation', 'turn_on', {'entity_id': automation})
    for automation in home_off_tuple:
        hass.services.call('automation', 'turn_off', {'entity_id': automation})

if SEND_MSG:
    if person_state == 'home':
        event_msg = '{0} has arrived home.'.format(person_label)
    else:
        event_msg = '{0} has departed.'.format(person_label)
    complete_msg = event_msg + house_msg + light_msg
    hass.services.call('notify', 'slack_assistant', {"message": complete_msg})
