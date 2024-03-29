import appdaemon.plugins.hass.hassapi as hass
import datetime
from time import sleep


class WakeupLight(hass.Hass):
    def initialize(self):
        self.INITIAL_LIGHT = 2
        self.MAX_LIGHT = 15
        self.OUT_OF_BED_DELAY = self.MAX_LIGHT + 5
        self.PRIOR_MINUTES = (self.MAX_LIGHT - self.INITIAL_LIGHT) * 2
        self.active = "input_boolean.wakeup_light"
        self.bedroom_lamp = "light.bedroom_lamp"
        self.bill_in_bed = "binary_sensor.sleepnumber_bill_bill_is_in_bed"
        self.bills_lamp = "light.bill_s_lamp"
        self.cricket_in_bed = "binary_sensor.sleepnumber_bill_cricket_is_in_bed"
        self.crickets_lamp = "light.cricket_s_lamp"
        self.debug_switch = "input_boolean.debug_wakeup_light"
        self.house_lights = "group.morning_lights"
        self.kitchen_lights = "group.kitchen_lights"
        self.light = "light.bedroom_dimmer"
        self.start_switch = "input_boolean.wakeup_light"
        self.sun = "sun.sun"
        self.wait_timer = "timer.wakup_light"
        self.wakeup_time = "input_datetime.wakeup_time"
        self.workday = "binary_sensor.workday"
        self.weekend_alarm = "input_boolean.wakeup_light_weekend"

        self.wake_time_handle = self.listen_state(self.on_wakeup_time_change, self.wakeup_time)

        self.reset()
        self.on_wakeup_time_change(None, None, None, None, None)

        init_msg = "Initialized Wakeup Light."
        self.call_service("notify/slack_assistant", message=init_msg)

    def reset(self):
        self.ticks = 0
        self.bills_lamp_on = False
        self.crickets_lamp_on = False

        try:
            self.cancel_listen_event(self.timer_handle)
        except AttributeError:
            self.log("No timer_handle to reset", level="WARNING")

        try:
            self.cancel_listen_state(self.light_handle)
        except AttributeError:
            self.log("No light_handle to reset", level="WARNING")

        try:
            self.cancel_listen_state(self.bill_bed_handle)
        except AttributeError:
            self.log("No bill_bed_handle to reset", level="WARNING")

        try:
            self.cancel_listen_state(self.cricket_bed_handle)
        except AttributeError:
            self.log("No cricket_bed_handle to reset", level="WARNING")

    def listen_for_out_of_bed(self):
        try:
            self.cancel_listen_state(self.bill_bed_handle)
        except AttributeError:
            self.log("No bill_bed_handle to clear", level="WARNING")

        try:
            self.cancel_listen_state(self.cricket_bed_handle)
        except AttributeError:
            self.log("No cricket_bed_handle to clear", level="WARNING")

        self.bill_bed_handle = self.listen_state(self.on_out_of_bed, self.bill_in_bed, new="off")
        self.cricket_bed_handle = self.listen_state(self.on_out_of_bed, self.cricket_in_bed, new="off")

    def on_begin_wakeup(self, kwargs):
        self.slack_debug("Wakeup started.")
        wakeup = True

        if self.get_state(self.weekend_alarm) == "on":
            self.slack_debug("Weeked wakeup is on.")
            wakeup = True
        elif self.get_state(self.workday) == "off":
            self.slack_debug("Not a work day today.")
            wakeup = False
        if self.get_state(self.active) == "off":
            self.slack_debug("Not waking up today.")
            wakeup = False

        if not wakeup:
            return

        self.timer_handle = self.listen_event(self.on_tick, "timer.finished", entity_id=self.wait_timer)
        self.light_handle = self.listen_state(self.on_switch_turned_off, self.light, new="off")
        self.on_tick(None, None, None)

    def on_out_of_bed(self, entity, attribute, old, new, kwargs):
        if entity == self.bill_in_bed:
            lamp = self.bills_lamp
            self.bills_lamp_on = True
        elif entity == self.cricket_in_bed:
            lamp = self.crickets_lamp
            self.crickets_lamp_on = True

        self.turn_on(lamp)
        self.slack_debug(f"Turned on {lamp}.")

        if self.bills_lamp_on and self.crickets_lamp_on:
            self.slack_debug(f"Turning on bedroom lamp.")
            self.turn_on(self.bedroom_lamp)

    def on_switch_turned_off(self, entity, attribute, old, new, kwargs):
        self.reset()
        self.slack_debug("Wakeup canceled.")

    def on_tick(self, event, data, kwargs):
        if self.ticks == 0:
            self.ticks = self.INITIAL_LIGHT
        else:
            self.ticks += 1

        if self.ticks == self.MAX_LIGHT:
            if self.get_state(self.sun) == "below_horizon":
                self.turn_on(self.house_lights)
            else:
                self.turn_on(self.kitchen_lights)
            self.listen_for_out_of_bed()

        if self.ticks <= self.MAX_LIGHT:
            self.turn_on(self.light, brightness_pct=str(self.ticks))
            self.slack_debug(f"Adjusting light to {self.ticks} percent.")

        elif self.ticks == self.OUT_OF_BED_DELAY:
            self.slack_debug("Wake up has ended.")

            if self.bills_lamp_on and self.crickets_lamp_on:
                self.turn_on(self.light, brightness_pct="80")
            else:
                self.turn_off(self.light)

            self.reset()

        self.call_service("timer/start", entity_id=self.wait_timer)

    def on_wakeup_time_change(self, entity, attribute, old, new, kwargs):
        try:
            self.cancel_timer(self.alarm_handle)
            self.slack_debug("Canceled time based handle.")
        except AttributeError:
            self.slack_debug("No time based handle to cancel.")

        if new is None:
            new = self.get_state(self.wakeup_time)

        hour, minute, second = new.split(":")
        alarm_time = datetime.time(int(hour), int(minute), int(second))
        today = datetime.date.today()
        today_time = datetime.datetime.combine(today, alarm_time)
        begin_time = today_time - datetime.timedelta(minutes=self.PRIOR_MINUTES)
        self.alarm_handle = self.run_daily(self.on_begin_wakeup, begin_time.time())
        self.slack_debug(f"Alarm time: {alarm_time}  Begin time: {begin_time.time()}")

    def slack_debug(self, message):
        debug = self.get_state(self.debug_switch) == "on"
        if debug:
            self.call_service("notify/slack_assistant", message=message)
