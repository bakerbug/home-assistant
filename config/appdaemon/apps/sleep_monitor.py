import appdaemon.plugins.hass.hassapi as hass


class SleepMonitor(hass.Hass):
    def initialize(self):
        self.COLD_TEMP = 65

        self.bedroom_fan = "fan.bedroom_fan"
        self.bedroom_fan_speed = "sensor.bedroom_fan_speed"
        self.bedroom_fan_low_temp = "input_number.bedroom_fan_low_temp"
        self.bedroom_tv = "media_player.bedroom_tv"
        self.bedroom_lamp = "switch.bedroom_lamp"
        self.bill_in_bed = "binary_sensor.sleepnumber_bill_bill_is_in_bed"
        self.bills_lamp = "switch.04200320b4e62d1291c4_1"
        self.cricket_in_bed = "binary_sensor.sleepnumber_bill_cricket_is_in_bed"
        self.crickets_lamp = "switch.04200320b4e62d1291c4_4"
        self.downstairs_temp = "sensor.downstairs_thermostat_temperature"
        self.floor_fan = "switch.wemo_alpha"
        self.fan_control = "input_boolean.enable_fan_control"
        self.living_area_lights = "group.living_area_lights"
        self.living_room_tv = "remote.harmony_hub"
        self.night_lights = "group.late_night_lights"
        self.sleep_monitor_active = "input_boolean.active_sleep_monitor"

        self.active_handle = self.listen_state(self.on_active_state, self.sleep_monitor_active)
        is_active = self.get_state(self.sleep_monitor_active) == "on"
        if is_active:
            self.on_active_state(None, None, None, "on", None)

        init_msg = "Initialized Sleep Monitor."
        self.call_service("notify/slack_assistant", message=init_msg)

    def on_active_state(self, entity, attribute, old, new, kwargs):
        if new == "on":
            self.bed_bill = self.listen_state(self.on_bed_change, self.bill_in_bed)
            self.bed_cricket = self.listen_state(self.on_bed_change, self.cricket_in_bed)
            self.downstairs_temp_handle = self.listen_state(self.on_temp_change, self.downstairs_temp)
            self.fan_handle = self.listen_state(self.on_fan_change, self.bedroom_fan_speed)
            self.tv_handle = self.listen_state(self.on_tv_change, self.bedroom_tv)
            self.slack_debug("Enabled sleep monitor handlers.")
        else:
            self.cancel_listen_state(self.bed_bill)
            self.cancel_listen_state(self.bed_cricket)
            self.cancel_listen_state(self.downstairs_temp_handle)
            self.cancel_listen_state(self.fan_handle)
            self.cancel_listen_state(self.tv_handle)
            self.slack_debug("Disabled sleep monitor handlers.")

    def on_bed_change(self, entity, attribute, old, new, kwargs):
        sun = self.get_state("sun.sun")
        bill_in_bed = self.get_state(self.bill_in_bed) == "on"
        cricket_in_bed = self.get_state(self.cricket_in_bed) == "on"
        self.slack_debug(f"(on_bed_change) {entity} went from {old} to {new} while sun is {sun}.")
        self.slack_debug(f"Bill in bed: {bill_in_bed}  Cricket in be: {cricket_in_bed}")

        # Set bedroom fan to low
        if sun == "above_horizon":
            old_speed = self.get_state(self.bedroom_fan_speed)

            if bill_in_bed or cricket_in_bed:
                downstairs_temp = int(self.get_state(self.downstairs_temp))
                fan_low_temp = int(float(self.get_state(self.bedroom_fan_low_temp)))
                if old_speed == "off" and downstairs_temp >= fan_low_temp:
                    self.set_fan_speed("low")
            elif not bill_in_bed and not cricket_in_bed:
                if old_speed == "low":
                    self.set_fan_speed("off")
        else:
            livingroom_tv_is_off = self.get_state(self.living_room_tv) == "off" or self.get_state(self.living_room_tv) == "idle"

            if livingroom_tv_is_off and bill_in_bed and cricket_in_bed:
                self.turn_off(self.living_area_lights)
                self.turn_on(self.fan_control)
                self.slack_debug("Turning off living area lights.")
            else:
                self.slack_debug(f"Not yet turning off lights: Livingroom TV: {livingroom_tv_is_off} Bill in bed: {bill_in_bed} Cricket in bed: {cricket_in_bed}")

            if old == "on" and new == "off":
                self.turn_on(self.night_lights)
                self.slack_debug("Turning on night lights.")

    def on_fan_change(self, entity, attribute, old, new, kwargs):
        self.slack_debug(f"(on_fan_change) {entity} went from {old} to {new}.")
        if new == "off" or new == "low":
            self.turn_off(self.floor_fan)
        elif new == "medium" or new == "high":
            self.turn_on(self.floor_fan)

    def on_temp_change(self, entity, attribute, old, new, kwargs):
        temperature = int(self.get_state(self.downstairs_temp))
        fan_speed = self.get_state(self.bedroom_fan_speed)

        if fan_speed == "off" or fan_speed == "low":
            return

        if temperature < self.COLD_TEMP:
            self.set_fan_speed("medium")
        else:
            self.set_fan_speed("high")

    def on_tv_change(self, entity, attribute, old, new, kwargs):
        if new == "unavailable" or old == "unavailable":
            return

        bedroom_fan_speed = self.get_state(self.bedroom_fan_speed)
        crickets_lamp_state = self.get_state(self.crickets_lamp)

        if bedroom_fan_speed != "off":
            if new == "standby" and (bedroom_fan_speed == "high" or bedroom_fan_speed == "medium"):
                self.slack_debug(f"Bedroom TV turned off while fan is on.  Turning on floor fan.")
                self.turn_on(self.floor_fan)
            elif old == "standby":
                self.slack_debug(f"Bedroom TV turned on while fan is on.  Turning off floor fan.")
                self.turn_off(self.floor_fan)
            else:
                self.slack_debug(f"Bedroom TV went from {old} to {new}. Not adjusting fan.")

        if crickets_lamp_state == "on":
            if new == "standby":
                self.turn_on(self.bedroom_lamp)
                self.turn_on(self.bills_lamp)
            elif old == "standby":
                self.turn_off(self.bedroom_lamp)
                self.turn_off(self.bills_lamp)

    def set_fan_speed(self, new_speed):
        old_speed = self.get_state(self.bedroom_fan_speed)

        if new_speed == old_speed:
            return

        self.call_service("fan/set_speed", entity_id=self.bedroom_fan, speed=new_speed)
        self.slack_debug(f"Set bedroom fan from {old_speed} to {new_speed}.")

    def slack_debug(self, message, prefix="Sleep Monitor"):
        debug = self.get_state("input_boolean.debug_sleep_monitor") == "on"
        if debug:
            if prefix:
                message = f"{prefix}: {message}"
            self.call_service("notify/slack_assistant", message=message)
