import appdaemon.plugins.hass.hassapi as hass
import datetime


class LaundryMonitor(hass.Hass):
    def initialize(self):
        self.debug_switch = "input_boolean.debug_laundry"
        clock = datetime.time(0, 0, 0)
        every_minute = self.run_minutely(self.check_power, clock)
        self.alexa = self.get_app("alexa_speak")
        self.washer_on = False
        self.power_limit = 3
        self.wait_minutes = 5
        self.ticks = 0

        init_msg = "Initialized Laundry Monitor."
        self.call_service("notify/slack_assistant", message=init_msg)

    def check_power(self, args):
        self.DEBUG = self.get_state(self.debug_switch) == "on"
        power_value = self.get_state("sensor.washing_machine_current_power")
        if power_value == "unavailable":
            return
        try:
            self.power_level = float(power_value)
        except ValueError:
            self.log(f"Unable to cast {power_value} to float.")
            return

        if self.DEBUG:
            self.alexa.announce(f"The laundry power is {self.power_level}", self.debug_switch)

        if self.washer_on:
            if self.power_level < self.power_limit:
                if self.ticks >= self.wait_minutes:
                    self.alexa.announce("The laundry has completed.", self.debug_switch)
                    self.washer_on = False
                    self.ticks = 0
                else:
                    self.ticks += 1
        elif self.power_level > self.power_limit:
            self.washer_on = True

        self.slack_debug(f"Laundry ticks: {self.ticks}")

    def slack_debug(self, message):
        debug = self.get_state("input_boolean.debug_laundry") == "on"
        if debug:
            self.call_service("notify/slack_assistant", message=message)
