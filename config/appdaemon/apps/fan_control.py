import appdaemon.plugins.hass.hassapi as hass

FAN_SPEED = {0: "off", 1: "low", 2: "medium", 3: "high"}
SUN_ELEV_HIGH = 60.00
SUN_ELEV_LOW = 25.00
SUN_AZ_HIGH = 180
WEATHER_SUNNY = ("sunny", "partlycloudy")
HIGH_OUTDOOR_TEMP = 80
HIGH_INDOOR_TEMP = 75
LOW_INDOOR_TEMP = 70


class FanControl(hass.Hass):
    def initialize(self):
        self.bed_b = "binary_sensor.sleepnumber_bill_bill_is_in_bed"
        self.bed_c = "binary_sensor.sleepnumber_bill_cricket_is_in_bed"
        self.ceiling_fan = "fan.living_room_ceiling_fan"
        self.switch_debug = "input_boolean.debug_fan_control"
        self.switch_enable = "input_boolean.enable_fan_control"
        self.switch_notify = "input_boolean.notify_fan_control"
        self.sun = "sun.sun"
        self.temp_down = "sensor.downstairs_thermostat_temperature"
        self.temp_up = "sensor.upstairs_thermostat_temperature"
        self.weather = "weather.khsv"

        # Conditions
        self.direct_sun = False
        self.house_asleep = False
        self.house_cool = False
        self.house_warm = False
        self.sky_clear = False
        self.weather_warm = False
        self.temp_delta = 0

        self.handle_enable = self.listen_state(
            self.on_enable_change, entity=self.switch_enable
        )
        init_state = self.get_state(self.switch_enable)
        self.on_enable_change(None, None, None, init_state, None)

        init_msg = "Initialized Fan Control."
        self.slack_msg(init_msg)

    def collect_data(self):
        self.on_bed_change(None, None, None, None, None)
        self.on_sun_change(None, None, None, None, None)
        self.on_temp_change(None, None, None, None, None)
        self.on_weather_change(None, None, None, None, None)

    def on_enable_change(self, entity, attribute, old, new, kwargs):
        if new == "on":
            self.collect_data()
            self.handle_b_bed = self.listen_state(self.on_bed_change, entity=self.bed_b)
            self.handle_c_bed = self.listen_state(self.on_bed_change, entity=self.bed_c)
            self.handle_sun = self.listen_state(self.on_sun_change, entity=self.sun)
            self.handle_temp_up = self.listen_state(
                self.on_temp_change, entity=self.temp_up
            )
            self.handle_temp_down = self.listen_state(
                self.on_temp_change, entity=self.temp_down
            )
            self.handle_weather = self.listen_state(
                self.on_weather_change, entity=self.weather
            )
            self.handle_fan_tick = self.run_minutely(self.check_fan, None)
            self.check_fan(None)

            self.slack_msg("Enabled Fan Control.")
        else:
            self.cancel_listen_state(self.handle_b_bed)
            self.cancel_listen_state(self.handle_c_bed)
            self.cancel_listen_state(self.handle_sun)
            self.cancel_listen_state(self.handle_temp_up)
            self.cancel_listen_state(self.handle_temp_down)
            self.cancel_listen_state(self.handle_weather)
            self.cancel_timer(self.handle_fan_tick)
            self.slack_msg("Disabled Fan Control.")

    def on_bed_change(self, entity, attribute, old, new, kwargs):
        result_asleep = False
        bill_asleep = self.get_state(self.bed_b) == "on"
        cricket_asleep = self.get_state(self.bed_c) == "on"

        if bill_asleep and cricket_asleep:
            result_asleep = True

        if result_asleep is True and self.house_asleep is False:
            self.slack_msg("The house is asleep.")
        if result_asleep is False and self.house_asleep is True:
            self.slack_msg("The house is awake.")

        self.house_asleep = result_asleep

    def on_sun_change(self, entity, attribute, old, new, kwargs):
        result = False
        sun_elevation = float(self.get_state(self.sun, attribute="elevation"))
        sun_azimuth = float(self.get_state(self.sun, attribute="azimuth"))
        self.slack_debug(f"Sun elevation is {sun_elevation}.")
        self.slack_debug(f"Sun azimuth is {sun_azimuth}.")

        if SUN_ELEV_LOW < sun_elevation < SUN_ELEV_HIGH:
            if sun_azimuth > SUN_AZ_HIGH:
                result = True
                self.slack_msg("The sun is now directly shining into the living room.")

        if self.direct_sun is True and result is False:
            self.slack_msg(
                "The sun is no longer directly shining into the living room."
            )

        self.direct_sun = result

    def on_temp_change(self, entity, attribute, old, new, kwargs):
        upstairs_temp = int(self.get_state(self.temp_up))
        downstairs_temp = int(self.get_state(self.temp_down))
        self.temp_delta = abs(upstairs_temp - downstairs_temp)

        if upstairs_temp >= HIGH_INDOOR_TEMP and downstairs_temp >= HIGH_INDOOR_TEMP:
            self.house_warm = True
            self.slack_msg(f"The house is warm.")
        else:
            self.house_warm = False

        if upstairs_temp <= LOW_INDOOR_TEMP or downstairs_temp <= LOW_INDOOR_TEMP:
            self.house_cool = True
            self.slack_msg(f"The house is cool.")
        else:
            self.house_cool = False

    def on_weather_change(self, entity, attribute, old, new, kwargs):
        sky = self.get_state(self.weather)
        outside_temp = int(self.get_state(self.weather, attribute="temperature"))

        if sky in WEATHER_SUNNY:
            result_clear = True
        else:
            result_clear = False

        if result_clear is True and self.sky_clear is False:
            self.slack_msg("The sky is now clear.")
        elif result_clear is False and self.sky_clear is True:
            self.slack_msg("The sky is no longer clear.")

        self.sky_clear = result_clear

        if outside_temp >= HIGH_OUTDOOR_TEMP:
            result_warm = True
        else:
            result_warm = False

        if result_warm is True and self.weather_warm is False:
            self.slack_msg("It is now warm outside.")
        elif result_warm is False and self.weather_warm is True:
            self.slack_msg("It is no longer warm outside.")

        self.weather_warm = result_warm

    def find_speed(self):
        # When to keep the fan off
        if self.house_cool and not self.house_asleep:
            return FAN_SPEED[0]

        # When the fan should always be high
        if self.house_warm:
            return FAN_SPEED[3]

        if self.direct_sun and self.sky_clear and self.weather_warm:
            return FAN_SPEED[3]

        # Determine variable speed
        return FAN_SPEED[max(self.temp_delta - 1, 0)]

    def check_fan(self, kwargs):
        current_speed = self.get_state(self.ceiling_fan, attribute="speed") or "off"
        self.slack_debug(f"Fan speed is {current_speed}.")

        new_speed = self.find_speed()
        self.slack_debug(f"Requested fan speed is {new_speed}.")

        if new_speed == current_speed:
            self.slack_debug("No fan adjustment needed.")
            return
        else:
            self.slack_msg(f"Adjusting fan from {current_speed} to {new_speed}.")
            self.call_service("fan/set_speed", entity_id=self.ceiling_fan, speed=new_speed)

    def slack_debug(self, message):
        debug = self.get_state(self.switch_debug) == "on"
        if debug:
            message = "Fan Control: " + message
            self.call_service("notify/slack_assistant", message=message)

    def slack_msg(self, message):
        notify = self.get_state(self.switch_notify) == "on"
        if notify:
            message = "Fan Control: " + message
            self.call_service("notify/slack_assistant", message=message)
