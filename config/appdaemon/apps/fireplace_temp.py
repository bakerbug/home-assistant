import appdaemon.plugins.hass.hassapi as hass
import random


class FireplaceTemp(hass.Hass):
    def initialize(self):
        self.max_indoor_temp_setting = "input_number.fireplace_max_indoor_temp"
        self.max_outdoor_temp_setting = "input_number.fireplace_max_outdoor_temp"
        self.OUTSIDE_FIRE_TEMP = 60
        self.upstairs = "sensor.upstairs_thermostat_temperature"
        self.downstairs = "sensor.downstairs_thermostat_temperature"
        self.outside = "weather.khsv"
        self.fireplace_switch = "input_boolean.fireplace_temperature"
        self.alexa = self.get_app("alexa_speak")
        self.debug_switch = "input_boolean.debug_fireplace_temp"

        self.request_handle = self.listen_state(self.on_request, self.fireplace_switch, new="on")

        self.yes_responses = (
            "Yes, a fire would be very nice!",
            "Yes, it is pretty chilly.",
            "Yes, I'm feeling a bit cool as well.",
            "Yes, a fire sounds very cozy.",
            "Oh yes!  Light it up!",
            "Yes, just don't burn down the house.",
        )

        self.turn_off(self.fireplace_switch)

        init_msg = "Initialized Fireplace Temperature."
        self.call_service("notify/slack_assistant", message=init_msg)

    def on_request(self, entity, attribute, old, new, kwargs):
        max_indoor_temp = int(float(self.get_state(self.max_indoor_temp_setting)))
        max_outdoor_temp = int(float(self.get_state(self.max_outdoor_temp_setting)))
        upstairs_temp = int(self.get_state(self.upstairs))
        downstairs_temp = int(self.get_state(self.downstairs))
        outside_temp = int(self.get_state(self.outside, attribute="temperature"))

        self.slack_debug(
            f"Max Indoor: {max_indoor_temp}, Max Outdoor: {max_outdoor_temp}, Upstairs: {upstairs_temp}, Downstairs: {downstairs_temp}, Outside: {outside_temp}"
        )

        msg = random.choice(self.yes_responses)

        if upstairs_temp > max_indoor_temp or downstairs_temp > max_indoor_temp:
            msg = "No, it is too warm inside to turn on the fireplace."
        elif outside_temp > max_outdoor_temp:
            msg = "No, it is too warm outside to turn on the fireplace."

        self.alexa.respond(msg)
        self.turn_off(self.fireplace_switch)

    def slack_debug(self, message):
        debug = self.get_state(self.debug_switch) == "on"
        if debug:
            self.call_service("notify/slack_assistant", message=message)
