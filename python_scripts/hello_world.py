first_name, last_name = data.get('name', 'world')
#last_name = data.get('world')
logger.warning("Hello {} {}".format(first_name, last_name))
hass.bus.fire(first_name, { "wow": "from a Python script!" })
