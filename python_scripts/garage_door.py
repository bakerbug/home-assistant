DEBUG = True

if DEBUG:
    debug_msg = "Script launched!"
    hass.services.call('notify', 'slack_assistant', {"message": debug_msg})

    garage_id = data.get('entity')
    debug_data = data.get('debug')
    debug_msg = "Received data: {}!".format(garage_id)
    hass.services.call('notify', 'slack_assistant', {"message": debug_msg})


garage_id = data.get('entity')
sun = hass.states.get('sun.sun').state
if garage_id is None:
    garage_msg = 'Garage door triggered but entity_id is None.'
else:
    label = hass.states.get(garage_id).attributes["friendly_name"]
    state = hass.states.get(garage_id).state
    garage_msg = '{} is {}. Sun is {}.'.format(label, state, sun)

hass.services.call('notify', 'slack_assistant', {"message": garage_msg})
