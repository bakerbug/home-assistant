import appdaemon.plugins.hass.hassapi as hass
from datetime import time

class GarageMonitor(hass.Hass):
    def initialize(self):
        self.message_times = {30, 45, 60}
        self.left_bay = "cover.left_bay"
        self.right_bay = "cover.right_bay"
        self.alexa = self.get_app("alexa_speak")
        self.left_bay_handle = self.listen_state(self.on_door_change, self.left_bay)
        self.right_bay_handle = self.listen_state(self.on_door_change, self.right_bay)
        self.debug_switch = "input_boolean.debug_garage_monitor"

        init_msg = "Initialized Garage Monitor."
        self.call_service("notify/slack_assistant", message=init_msg)

    def on_door_change(self, entity, attribute, old, new, kwargs):
        self.slack_debug(f"Detected {entity} is {new}.")
        if new == "open":
            try:
                self.cancel_timer(self.timer_handle)
            except AttributeError:
                pass

            self.timer_ticks = 0
            self.timer_handle = self.run_minutely(self.on_tick, time(0, 0, 0))

    def on_tick(self, kwargs):
        self.timer_ticks += 1
        if self.timer_ticks not in self.message_times:
            return

        left_open = self.get_state(self.left_bay) == "open"
        right_open = self.get_state(self.right_bay) == "open"
        self.slack_debug(f"Left bay is {left_open}, Right bay is {right_open}, Ticks: {self.timer_ticks}.")

        msg = "One of the garage doors may be open."
        if left_open and right_open:
            msg = f"The left and right bays have been open for {self.timer_ticks} minutes."
        elif left_open:
            msg = f"The left bay has been open for {self.timer_ticks} minutes."
        elif right_open:
            msg = f"The right bay has been open for {self.timer_ticks} minutes."

        if not left_open and not right_open:
            self.cancel_timer(self.timer_handle)
            self.slack_debug(f"Canceled garage monitor timer.")
        else:
            self.alexa.announce(msg, self.debug_switch)

    def slack_debug(self, message):
        debug = self.get_state(self.debug_switch) == "on"
        if debug:
            self.call_service("notify/slack_assistant", message=message)
