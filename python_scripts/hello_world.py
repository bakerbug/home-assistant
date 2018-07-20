first_name = data.get('fname')
last_name = data.get('lname')
logger.warning("Hello {} {}".format(first_name, last_name))
hass.bus.fire(first_name, { "wow": "from a Python script!" })
