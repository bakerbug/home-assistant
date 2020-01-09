import appdaemon.plugins.hass.hassapi as hass

class WakeupLight(hass.Hass):

    def initialize(self):
        self.INITIAL_LIGHT = 5
        self.MAX_LIGHT = 20
        self.OUT_OF_BED_DELAY = 5
        self.ticks = 0
        self.bedroom_lamp = "switch.bedroom_lamp"
        self.bill_in_bed = "binary_sensor.sleepnumber_bill_bill_is_in_bed"
        self.bills_lamp = "switch.04200320b4e62d1291c4_1"
        self.cricket_in_bed = "binary_sensor.sleepnumber_bill_cricket_is_in_bed"
        self.crickets_lamp = "switch.04200320b4e62d1291c4_4"
        self.light = "light.bedroom_dimmer"
        self.start_switch = "input_boolean.wakeup_light"
        self.wait_timer = "timer.wakup_light"

        self.switch_handle = self.listen_state(self.on_wakeup, self.start_switch)

        init_msg = "Initialized Wakeup Light."
        self.call_service("notify/slack_assistant", message=init_msg)

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

            self.ticks = 0

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
        elif entity == self.cricket_in_bed:
            lamp = self.crickets_lamp

        self.turn_on(lamp)
        self.slack_debug(f"Turned on {lamp}.")

        bill_lamp_on = self.get_state(self.bills_lamp) == "on"
        self.slack_debug(f"Bill's lamp on: {bill_lamp_on}.")
        cricket_lamp_on = self.get_state(self.crickets_lamp) == "on"
        self.slack_debug(f"Cricket's lamp on: {cricket_lamp_on}.")
        if bill_lamp_on and cricket_lamp_on:
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
            self.turn_off(self.light)

        self.call_service("timer/start", entity_id=self.wait_timer)

    def slack_debug(self, message):
        debug = self.get_state("input_boolean.debug_wakeup_light") == "on"
        if debug:
            self.call_service("notify/slack_assistant", message=message)
