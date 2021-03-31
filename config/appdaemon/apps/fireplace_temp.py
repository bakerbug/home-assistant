import appdaemon.plugins.hass.hassapi as hass
import random


class FireplaceTemp(hass.Hass):
    def initialize(self):
        self.max_indoor_temp_setting = "input_number.fireplace_max_indoor_temp"
        self.max_outdoor_temp_setting = "input_number.fireplace_max_outdoor_temp"
        self.shutdown_temp = "input_number.fireplace_shutdown_temp"
        self.OUTSIDE_FIRE_TEMP = 60
        self.upstairs = "sensor.upstairs_thermostat_temperature"
        self.upstairs_last = 0
        self.downstairs = "sensor.downstairs_thermostat_temperature"
        self.outside = "weather.khsv"
        self.fireplace_switch = "input_boolean.fireplace_temperature"
        self.alexa = self.get_app("alexa_speak")
        self.debug_switch = "input_boolean.debug_fireplace_temp"

        self.request_handle = self.listen_state(self.on_request, self.fireplace_switch, new="on")
        self.upstairs_handle = self.listen_state(self.temp_change, self.upstairs)

        self.yes_responses = (
            "Yes, a fire would be very nice!",
            "Yes, it is pretty chilly.",
            "Yes, I'm feeling a bit cool as well.",
            "Yes, a fire sounds very cozy.",
            "Oh yes!  Light it up!",
            "Yes, just don't burn down the house.",
            "Yes!  Light it up, watch it burn.",
        )

        self.turn_off(self.fireplace_switch)
        self._get_current_temp()

        init_msg = "Initialized Fireplace Temperature."
        self.call_service("notify/slack_assistant", message=init_msg)

    def on_request(self, entity, attribute, old, new, kwargs):
        self.turn_off(self.fireplace_switch)
        max_indoor_temp = int(float(self.get_state(self.max_indoor_temp_setting)))
        max_outdoor_temp = int(float(self.get_state(self.max_outdoor_temp_setting)))
        self._get_current_temp()

        self.slack_debug(
            f"Max Indoor: {max_indoor_temp}, Max Outdoor: {max_outdoor_temp}, Upstairs: {self.upstairs_current_temp}, Downstairs: {self.downstairs_current_temp}, Outside: {self.outside_current_temp}"
        )

        msg = random.choice(self.yes_responses)

        if self.upstairs_current_temp > max_indoor_temp or self.downstairs_current_temp > max_indoor_temp:
            msg = "No, it is too warm inside to turn on the fireplace."
        elif self.outside_current_temp > max_outdoor_temp:
            msg = "No, it is too warm outside to turn on the fireplace."

        self.alexa.respond(msg)

    def temp_change(self, entity, attribute, old, new, kwargs):
        upstairs_setting = self.get_state("climate.upstairs")
        if upstairs_setting != "heat":
            self.slack_debug("Temperature change, but the heat is not on.")
            return
        self._get_current_temp()
        self.slack_debug(f"Upstairs temp changed to {self.upstairs_current_temp}.")
        shutdown_temp = int(float(self.get_state(self.shutdown_temp)))
        max_outdoor_temp = int(float(self.get_state(self.max_outdoor_temp_setting)))
        max_indoor_temp = int(float(self.get_state(self.max_indoor_temp_setting)))

        if self.outside_current_temp >= max_outdoor_temp:
            return

        if self.upstairs_current_temp >= shutdown_temp and self.upstairs_current_temp > self.upstairs_last_temp:
            msg = f"The upstairs temperature is {self.upstairs_current_temp}.  It is time to turn off the fireplace."
            self.alexa.announce(msg, self.debug_switch)

        elif self.upstairs_current_temp == max_indoor_temp - 1 and self.upstairs_current_temp < self.upstairs_last_temp:
            msg = f"It is getting cool in the house.  Would you like to turn on the fireplace?"
            self.slack_debug(msg)
            self.alexa.announce(msg, self.debug_switch)

    def _get_current_temp(self):
        self.slack_debug("Getting current temperatures:")
        try:
            self.upstairs_current_temp
        except AttributeError:
            self.upstairs_current_temp = 0
        self.upstairs_last_temp = self.upstairs_current_temp
        self.slack_debug(f"upstairs_last_temp is now: {self.upstairs_last_temp}")
        self.upstairs_current_temp = int(self.get_state(self.upstairs))
        self.slack_debug(f"upstairs_current_temp is now: {self.upstairs_current_temp}")
        self.downstairs_current_temp = int(self.get_state(self.downstairs))
        self.slack_debug(f"downstairs_current_temp is now: {self.downstairs_current_temp}")
        self.outside_current_temp = int(self.get_state(self.outside, attribute="temperature"))
        self.slack_debug(f"outside_current_temp is now: {self.outside_current_temp}")

    def slack_debug(self, message):
        debug = self.get_state(self.debug_switch) == "on"
        message = "(fireplace_temp) " + message
        if debug:
            self.call_service("notify/slack_assistant", message=message)
