"""
Enables or disables automations based on away status.
"""

away_on_list = {'automation.hvac_balancing', 'automation.lights_out_when_away', }
away_off_list = {'automation.lights_on_at_early_sunset', }
home_on_list = {'automation.lights_on_at_early_sunset', }
home_off_list = {'automation.lights_out_when_away', }
away_state = hass.states.get('binary_sensor.bayberry_away').state

if away_state == 'on':
    for automation in away_on_list:
        hass.services.call('automation', 'turn_on', {'entity_id': automation})
    for automation in away_off_list:
        hass.services.call('automation', 'turn_off', {'entity_id': automation})
elif away_state == 'off':
    for automation in home_on_list:
        hass.services.call('automation', 'turn_on', {'entity_id': automation})
    for automation in home_off_list:
        hass.services.call('automation', 'turn_off', {'entity_id': automation})
