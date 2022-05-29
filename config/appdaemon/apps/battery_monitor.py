import appdaemon.plugins.hass.hassapi as hass
import datetime


class BatteryMon(hass.Hass):
    def initialize(self):
        self.alexa = self.get_app("alexa_speak")
        self.schedule = datetime.time(16, 0, 0)
        self.front_door = "sensor.front_door_battery"
        self.back_door = "sensor.back_door_battery"
        self.orbit_tracker = "sensor.orbit_battery_level"
        self.trigger = "input_boolean.battery_monitor"

        self.trigger_handler = self.listen_state(self.on_trigger, self.trigger, new="on")
        self.daily_check = self.run_daily(self.on_schedule, self.schedule)
        self.slack_debug("Initialized Battery Monitor.")

    def on_schedule(self, kwargs):
        self.battery_check()

    def on_trigger(self, entity, attribute, old, new, kwargs):
        self.turn_off(self.trigger)
        self.battery_check()

    def battery_check(self):
        self.turn_off(self.trigger)
        back_level = int(self.get_state(self.back_door))
        front_level = int(self.get_state(self.front_door))
        orbit_level = int(self.get_state(self.orbit_tracker))

        msg = None

        if back_level <= 30:
            msg = f"The battery level for the back door lock is {back_level} percent.  "
            self.alexa.notify(msg)

        if front_level <= 30:
            msg = f"The battery level for the front door lock is {front_level} percent.  "
            self.alexa.notify(msg)

        if orbit_level <= 40:
            msg = f"The battery level for Orbit's location tracker is {orbit_level} percent.  Please recharge the tracker now.  "
            self.alexa.notify(msg)

    def slack_debug(self, message):
        self.call_service("notify/slack_assistant", message=message)
