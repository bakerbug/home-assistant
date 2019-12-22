import appdaemon.plugins.hass.hassapi as hass

class SleepMonitor(hass.Hass):

    def initialize(self):
        self.COLD_TEMP = 65

        self.bedroom_fan = "fan.bedroom_fan"
        self.bedroom_tv = "media_player.bedroom_tv"
        self.bedroom_lamp = "switch.bedroom_lamp"
        self.bill_in_bed = "binary_sensor.sleepnumber_bill_bill_is_in_bed"
        self.bills_lamp = "switch.04200320b4e62d1291c4_1"
        self.cricket_in_bed = "binary_sensor.sleepnumber_bill_cricket_is_in_bed"
        self.crickets_lamp = "switch.04200320b4e62d1291c4_4"
        self.downstairs_temp = "sensor.downstairs_thermostat_temperature"
        self.floor_fan = "switch.wemo_alpha"
        self.sleep_monitor_active = "input_boolean.active_sleep_monitor"

        self.active_handle = self.listen_state(self.on_active_state, self.sleep_monitor_active)
        is_active = self.get_state(self.sleep_monitor_active) == "on"
        if is_active:
            self.on_active_state(None, None, None, "on", None)

        init_msg = "Initialized Sleep Monitor."
        self.call_service("notify/slack_assistant", message=init_msg)

    def on_active_state(self, entity, attribute, old, new, kwargs):
        if new == "on":
            self.downstairs_temp_handle = self.listen_state(self.on_temp_change, self.downstairs_temp)
            self.fan_handle = self.listen_state(self.on_fan_change, self.bedroom_fan)
            self.tv_handle = self.listen_state(self.on_tv_change, self.bedroom_tv)
            self.slack_debug("Enabled sleep monitor handlers.")
        else:
            self.cancel_listen_state(self.downstairs_temp_handle)
            self.cancel_listen_state(self.fan_handle)
            self.cancel_listen_state(self.tv_handle)
            self.slack_debug("Disabled sleep monitor handlers.")

    def on_fan_change(self, entity, attribute, old, new, kwargs):
        tv_state = self.get_state(self.bedroom_tv)

        if tv_state != "standby":
            return

        if new == 'on':
            self.turn_on(self.floor_fan)
        else:
            self.turn_off(self.floor_fan)

    def on_temp_change(self, entity, attribute, old, new, kwargs):
        temperature = int(self.get_state(self.downstairs_temp))

        if temperature < self.COLD_TEMP:
            self.set_fan_speed("medium")
        else:
            self.set_fan_speed("high")

    def on_tv_change(self, entity, attribute, old, new, kwargs):
        bedroom_fan_state = self.get_state(self.bedroom_fan)
        crickets_lamp_state = self.get_state(self.crickets_lamp)

        if bedroom_fan_state == "on":
            if new == "standby":
                self.turn_on(self.floor_fan)
            elif old == "standby":
                self.turn_off(self.floor_fan)

        if crickets_lamp_state == "on":
            if new == "standby":
                self.turn_on(self.bedroom_lamp)
                self.turn_on(self.bills_lamp)
            elif old == "standby":
                self.turn_off(self.bedroom_lamp)
                self.turn_off(self.bills_lamp)

    def set_fan_speed(self, new_speed):
        fan_state = self.get_state(self.bedroom_fan)
        fan_speed = self.get_state(self.bedroom_fan, attribute="speed")

        if fan_state == "off" or new_speed == fan_speed:
            return

        self.call_service("fan/set_speed", entity_id=self.bedroom_fan, speed=new_speed)
        self.slack_debug(f"Set bedroom fan to {new_speed}.")

    def slack_debug(self, message):
        debug = self.get_state("input_boolean.debug_sleep_monitor") == "on"
        if debug:
            self.call_service("notify/slack_assistant", message=message)
