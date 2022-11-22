import appdaemon.plugins.hass.hassapi as hass
import datetime

LOW_BATTERY_LEVEL = 40

class BatteryMon(hass.Hass):
    def initialize(self):
        self.alexa = self.get_app("alexa_speak")
        self.schedule = datetime.time(16, 0, 0)
        self.front_door = "sensor.front_door_battery"
        self.front_door_contact = "sensor.front_door_battery_2"
        self.freezer_door = "sensor.freezer_door_battery"
        self.back_door = "sensor.back_door_battery"
        self.orbit_tracker = "sensor.orbit_battery_level"
        self.trigger = "input_boolean.battery_monitor"

        self.trigger_handler = self.listen_state(self.on_trigger, self.trigger, new="on")
        self.daily_check = self.run_daily(self.on_schedule, self.schedule)
        self.slack_debug("Initialized Battery Monitor.")

    def on_schedule(self, kwargs):
        schedule_msg = self.battery_check()
        if schedule_msg != "":
            self.alexa.notify(schedule_msg)

    def on_trigger(self, entity, attribute, old, new, kwargs):
        self.turn_off(self.trigger)
        trigger_msg = self.battery_check()
        if trigger_msg == "":
            msg = f"All monitored batteries are above {LOW_BATTERY_LEVEL} percent."
            self.alexa.respond(msg)
        else:
            self.alexa.respond(trigger_msg)

    def battery_check(self):
        self.turn_off(self.trigger)
        back_level = int(self.get_state(self.back_door))
        front_level = int(self.get_state(self.front_door))
        front_contact_level = int(self.get_state(self.front_door_contact))
        freezer_level = int(self.get_state(self.freezer_door))
        orbit_level = int(self.get_state(self.orbit_tracker))

        msg = ""

        if back_level <= LOW_BATTERY_LEVEL:
            msg = msg + f"The battery level for the back door lock is {back_level} percent.  "

        if front_level <= LOW_BATTERY_LEVEL:
            msg = msg + f"The battery level for the front door lock is {front_level} percent.  "

        if front_contact_level <= LOW_BATTERY_LEVEL:
            msg = msg + f"The battery level for the front door contact sensor is {front_contact_level} percent.  "

        if freezer_level <= LOW_BATTERY_LEVEL:
            msg = msg + f"The battery level for the freezer door contact sensor is {freezer_level} percent.  "

        if orbit_level <= LOW_BATTERY_LEVEL:
            msg = msg + f"The battery level for Orbit's location tracker is {orbit_level} percent.  Please recharge the tracker now.  "

        return msg

    def slack_debug(self, message):
        self.call_service("notify/slack_assistant", message=message)
