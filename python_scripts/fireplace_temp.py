import appdaemon.plugins.hass.hassapi as hass
import random

class FireplaceTemp(hass.Hass):

    def initialize(self):
        self.INSIDE_FIRE_TEMP = 67
        self.OUTSIDE_FIRE_TEMP = 60
        self.upstairs = "sensor.upstairs_thermostat_temperature"
        self.downstairs = "sensor.downstairs_thermostat_temperature"
        self.outside = "weather.dark_sky"
        self.fireplace_switch = "input_boolean.fireplace_temperature"
        self.alexa = self.get_app("alexa_speak")

        self.request_handle = self.listen_state(self.on_request, self.fireplace_switch, new="on")

        self.yes_responses = ("Yes, a fire would be very nice!",
                              "Yes, it is pretty chilly.",
                              "Yes, I'm feeling a bit cool as well.",
                              "Yes, I'd like to warm up also.")

        init_msg = "Initialized Fireplace Temperature."
        self.call_service("notify/slack_assistant", message=init_msg)

    def on_request(self, entity, attribute, old, new, kwargs):
        upstairs_temp = int(self.get_state(self.upstairs))
        downstairs_temp = int(self.get_state(self.downstairs))
        outside_temp = int(self.get_state(self.outside, attribute="temperature"))

        msg = random.choice(self.yes_responses)

        if upstairs_temp > self.INSIDE_FIRE_TEMP or downstairs_temp > self.INSIDE_FIRE_TEMP:
            msg = "No, it is too warm inside to turn on the fireplace."
        elif outside_temp > self.OUTSIDE_FIRE_TEMP:
            msg = "No, it is too warm outside to turn on the fireplace."

        self.alexa.respond(msg)
        self.turn_off(self.fireplace_switch)