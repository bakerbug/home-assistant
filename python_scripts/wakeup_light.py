import appdaemon.plugins.hass.hassapi as hass
import datetime
from time import sleep


class WakeupLight(hass.Hass):

    def initialize(self):
        self.INITIAL_LIGHT = 5
        self.MAX_LIGHT = 20
        self.OUT_OF_BED_DELAY = self.MAX_LIGHT + 5
        self.bedroom_lamp = "switch.bedroom_lamp"
        self.bill_in_bed = "binary_sensor.sleepnumber_bill_bill_is_in_bed"
        self.bills_lamp = "switch.04200320b4e62d1291c4_1"
        self.cricket_in_bed = "binary_sensor.sleepnumber_bill_cricket_is_in_bed"
        self.crickets_lamp = "switch.04200320b4e62d1291c4_4"
        self.light = "light.bedroom_dimmer"
        self.start_switch = "input_boolean.wakeup_light"
        self.wait_timer = "timer.wakup_light"

        self.switch_handle = self.listen_state(self.on_wakeup, self.start_switch)

        self.reset()

        init_msg = "Initialized Wakeup Light."
        self.call_service("notify/slack_assistant", message=init_msg)

    def reset(self):
        self.ticks = 0
        self.bills_lamp_on = False
        self.crickets_lamp_on = False


    def on_wakeup(self, entity, attribute, old, new, kwargs):
        if new == "on":
            self.slack_debug("Wakeup started.")
            self.timer_handle = self.listen_event(self.on_tick, "timer.finished", entity_id=self.wait_timer)
            self.light_handle = self.listen_state(self.on_switch_turned_off, self.light, new="off")
            self.bill_bed_handle = self.listen_state(self.on_out_of_bed, self.bill_in_bed, new="off")
            self.cricket_bed_handle = self.listen_state(self.on_out_of_bed, self.cricket_in_bed, new="off")
            self.on_tick("bogus", "bogus", "bogus")
        elif new == "off":
            if self.ticks < self.MAX_LIGHT:
                self.slack_debug("Wakeup canceled.")
                self.turn_off(self.light)

            self.reset()

            try:
                self.cancel_listen_event(self.timer_handle)
                self.cancel_listen_state(self.light_handle)
                self.cancel_listen_state(self.bill_bed_handle)
                self.cancel_listen_state(self.cricket_bed_handle)
            except AttributeError:
                pass

    def on_out_of_bed(self, entity, attribute, old, new, kwargs):
        if entity == self.bill_in_bed:
            lamp = self.bills_lamp
            self.bills_lamp_on = True
        elif entity == self.cricket_in_bed:
            lamp = self.crickets_lamp
            self.crickets_lamp_on = True

        self.turn_on(lamp)
        self.slack_debug(f"Turned on {lamp}.")

        if self.bill_lamp_on and self.cricket_lamp_on:
            self.slack_debug(f"Turning on bedroom lamp.")
            self.turn_on(self.bedroom_lamp)

    def on_switch_turned_off(self, entity, attribute, old, new, kwargs):
        self.turn_off(self.start_switch)

    def on_tick(self, event, data, kwargs):
        if self.ticks == 0:
            self.ticks = self.INITIAL_LIGHT
        else:
            self.ticks += 1

        if self.ticks <= self.MAX_LIGHT:
            self.turn_on(self.light, brightness_pct=str(self.ticks))
            self.slack_debug(f"Adjusting light to {self.ticks} percent.")

        elif self.ticks == self.OUT_OF_BED_DELAY:
            self.cancel_listen_event(self.timer_handle)
            self.turn_off(self.start_switch)
            self.turn_on(self.light, brightness_pct="80")
            self.slack_debug("Wake up has ended.")

        self.call_service("timer/start", entity_id=self.wait_timer)

    def on_wakeup_time_change(self, entity, attribute, old, new, kwargs):
        # Not yet wired in
        try:
            self.cancel_timer(self.wakeup_time_handle)
        except AttributeError:
            pass

        hour, minute, second = new.split(':')
        time = datetime.time(hour, minute, second)
        day = datetime.date.today()
        alarm_time = datetime.datetime.combine(day, time)
        begin_time = alarm_time - datetime.timedelta(minutes=self.PRIOR_MINUTES)
        self.wakup_time_handle = self.run_at(self.on_begin_wakeup, begin_time)

    def slack_debug(self, message):
        debug = self.get_state("input_boolean.debug_wakeup_light") == "on"
        if debug:
            self.call_service("notify/slack_assistant", message=message)
