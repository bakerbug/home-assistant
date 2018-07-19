first_name, last_name = data.get('name', 'world')
logger.warning("Hello {} {}".format(first_name, last_name))
hass.bus.fire(name, { "wow": "from a Python script!" })
