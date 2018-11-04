"""
Enables or disables automations based on away status.
"""

SEND_MSG = False

away_on_list = {'automation.hvac_balancing', 'automation.lights_out_when_away', 'automation.lights_on_when_away', }
away_off_list = {'automation.lights_on_at_early_sunset', 'automation.lights_on_at_sunset', }
home_on_list = {'automation.lights_on_at_early_sunset', 'automation.lights_on_at_sunset', }
home_off_list = {'automation.lights_out_when_away', 'automation.lights_on_when_away', }
nest_away = hass.states.get('binary_sensor.bayberry_away').state
bill_phone = hass.states.get('device_tracker.bill_cell').state
cricket_phone = hass.states.get('device_tracker.cricket_cell').state

away_state = True
if nest_away == 'off' or bill_phone == 'home' or cricket_phone == 'home':
    away_state = False

if away_state:
    for automation in away_on_list:
        hass.services.call('automation', 'turn_on', {'entity_id': automation})
    for automation in away_off_list:
        hass.services.call('automation', 'turn_off', {'entity_id': automation})
else:
    for automation in home_on_list:
        hass.services.call('automation', 'turn_on', {'entity_id': automation})
    for automation in home_off_list:
        hass.services.call('automation', 'turn_off', {'entity_id': automation})

if SEND_MSG:
    msg = "Nest is {0}.  Bill is {1}.  Cricket is {2}.".format(nest_away, bill_phone, cricket_phone)
    hass.services.call('notify', 'slack_assistant', {"message": msg})
