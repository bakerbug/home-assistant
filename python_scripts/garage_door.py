garage_id = data.get('entity')
msg = "Entity is: {}.".format(garage_id)
hass.services.call('notify', 'slack_assistant', {"message": msg})

if garage_id is None:
    garage_msg = 'Garage door triggered but entity_id is None.'
else:
    label = hass.states.get(garage_id).attributes["friendly_name"]
    state = hass.states.get(garage_id).state
    garage_msg = '{} is {}.'.format(label, state)

sun = hass.states.get('sun.sun').state
hass.services.call('notify', 'slack_assistant', {"message": garage_msg})
