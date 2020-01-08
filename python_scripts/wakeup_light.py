import appdaemon.plugins.hass.hassapi as hass

class WakeupLight(hass.Hass):

    def initialize(self):
        self.INITIAL_LIGHT = 5
        self.MAX_LIGHT = 20
        self.ticks = 0
        self.light = "light.bedroom_dimmer"
        self.start_switch = "input_boolean.wakeup_light"
        self.wait_timer = "timer.wakup_light"

        self.switch_handler = self.listen_state(self.on_wakeup, self.start_switch)

        init_msg = "Initialized Wakeup Light."
        self.call_service("notify/slack_assistant", message=init_msg)

    def on_wakeup(self, entity, attribute, old, new, kwargs):
        if new == "on":
            self.slack_debug("Wakeup started.")
            self.timer_handler = self.listen_event(self.on_tick, "timer.finished", entity_id=self.wait_timer)
            self.light_handle = self.listen_state(self.on_switch_turned_off, self.light, new="off")
            self.on_tick("bogus", "bogus", "bogus")
        elif new == "off":
            if self.ticks < self.MAX_LIGHT:
                self.slack_debug("Wakeup canceled.")
                self.turn_off(self.light)

            self.ticks = 0

            try:
                self.cancel_listen_event(self.timer_handler)
                self.cancel_lisen_state(self.light_handle)
            except AttributeError:
                pass

    def on_switch_turned_off(self, entity, attribute, old, new, kwargs):
        self.turn_off(self.start_switch)

    def on_tick(self, event, data, kwargs):
        if self.ticks == 0:
            self.ticks = self.INITIAL_LIGHT
        else:
            self.ticks += 1

        self.turn_on(self.light, brightness_pct=str(self.ticks))
        self.slack_debug(f"Adjusting light to {self.ticks} percent.")

        if self.ticks == self.MAX_LIGHT:
            self.cancel_listen_event(self.timer_handler)
            self.turn_off(self.start_switch)
            self.slack_debug(f"Full brightness reached.")
        else:
            self.call_service("timer/start", entity_id=self.wait_timer)

    def slack_debug(self, message):
        debug = self.get_state("input_boolean.debug_wakeup_light") == "on"
        if debug:
            self.call_service("notify/slack_assistant", message=message)