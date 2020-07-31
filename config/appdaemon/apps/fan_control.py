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
        self.tower_fan = "switch.wemo_charlie"
        self.weather = "weather.khsv"

        # Conditions
        self.direct_sun = False
        self.house_asleep = False
        self.house_cool = False
        self.house_upstairs_warm = False
        self.house_downstairs_warm = False
        self.sky_clear = False
        self.weather_warm = False
        self.temp_delta = 0

        self.handle_enable = self.listen_state(self.on_enable_change, entity=self.switch_enable)
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
        self.slack_debug("Called on_enable_change.")
        if new == "on":
            self.collect_data()
            self.handle_b_bed = self.listen_state(self.on_bed_change, entity=self.bed_b)
            self.handle_c_bed = self.listen_state(self.on_bed_change, entity=self.bed_c)
            self.handle_sun = self.listen_state(self.on_sun_change, entity=self.sun, attribute="elevation")
            self.handle_temp_up = self.listen_state(self.on_temp_change, entity=self.temp_up)
            self.handle_temp_down = self.listen_state(self.on_temp_change, entity=self.temp_down)
            self.handle_weather = self.listen_state(self.on_weather_change, entity=self.weather)
            # self.handle_fan_tick = self.run_minutely(self.check_fan, None)
            self.check_fans()

            self.slack_msg("Enabled Fan Control.")
        else:
            self.cancel_listen_state(self.handle_b_bed)
            self.cancel_listen_state(self.handle_c_bed)
            self.cancel_listen_state(self.handle_sun)
            self.cancel_listen_state(self.handle_temp_up)
            self.cancel_listen_state(self.handle_temp_down)
            self.cancel_listen_state(self.handle_weather)
            # self.cancel_timer(self.handle_fan_tick)
            self.slack_msg("Disabled Fan Control.")

    def on_bed_change(self, entity, attribute, old, new, kwargs):
        self.slack_debug("Called on_bed_change.")
        need_update = False
        result_asleep = False
        bill_asleep = self.get_state(self.bed_b) == "on"
        cricket_asleep = self.get_state(self.bed_c) == "on"

        if bill_asleep and cricket_asleep:
            result_asleep = True

        if result_asleep is True and self.house_asleep is False:
            need_update = True
            self.slack_msg("The house is asleep.")
        if result_asleep is False and self.house_asleep is True:
            need_update = True
            self.slack_msg("The house is awake.")

        if need_update:
            self.house_asleep = result_asleep
            self.check_fans()

    def on_sun_change(self, entity, attribute, old, new, kwargs):
        self.slack_debug("Called on_sun_change.")
        need_update = False
        result = False
        sun_elevation = float(self.get_state(self.sun, attribute="elevation"))
        sun_azimuth = float(self.get_state(self.sun, attribute="azimuth"))
        self.slack_debug(f"Sun elevation is {sun_elevation}.")
        self.slack_debug(f"Sun azimuth is {sun_azimuth}.")

        if SUN_ELEV_LOW < sun_elevation < SUN_ELEV_HIGH:
            if sun_azimuth > SUN_AZ_HIGH:
                result = True

        if result is True and self.direct_sun is False:
            need_update = True
            self.slack_msg("The sun is now directly shining into the living room.")
        elif result is False and self.direct_sun is True:
            need_update = True
            self.slack_msg("The sun is no longer directly shining into the living room.")

        if need_update:
            self.direct_sun = result
            self.check_fans()

    def on_temp_change(self, entity, attribute, old, new, kwargs):
        self.slack_debug("Called on_temp_change.")
        need_update = False
        result_up_warm = False
        result_down_warm = False
        result_cool = False
        upstairs_temp = int(self.get_state(self.temp_up))
        downstairs_temp = int(self.get_state(self.temp_down))
        self.temp_delta = abs(upstairs_temp - downstairs_temp)

        if upstairs_temp >= HIGH_INDOOR_TEMP:
            result_up_warm = True

        if downstairs_temp >= HIGH_INDOOR_TEMP:
            result_down_warm = True

        if upstairs_temp <= LOW_INDOOR_TEMP or downstairs_temp <= LOW_INDOOR_TEMP:
            result_cool = True

        if result_up_warm is True and self.house_upstairs_warm is False:
            need_update = True
            self.slack_msg(f"The upstairs is warm.")
        elif result_up_warm is False and self.house_upstairs_warm is True:
            need_update = True
            self.slack_msg("The upstairs is no longer warm.")

        if result_down_warm is True and self.house_downstairs_warm is False:
            need_update = True
            self.slack_msg(f"The downstairs is warm.")
        elif result_down_warm is False and self.house_downstairs_warm is True:
            need_update = True
            self.slack_msg("The downstairs is no longer warm.")

        if result_cool is True and self.house_cool is False:
            need_update = True
            self.slack_msg("The house is cool.")
        elif result_cool is False and self.house_cool is True:
            need_update = True
            self.slack_msg("The house is no longer cool.")

        if need_update:
            self.house_upstairs_warm = result_up_warm
            self.house_downstairs_warm = result_down_warm
            self.house_cool = result_cool

        # Always check fans when the temperature changes.
        self.check_fans()

    def on_weather_change(self, entity, attribute, old, new, kwargs):
        self.slack_debug("Called on_weather_change.")
        need_update = False
        sky = self.get_state(self.weather)
        outside_temp = int(self.get_state(self.weather, attribute="temperature"))

        if sky in WEATHER_SUNNY:
            result_clear = True
        else:
            result_clear = False

        if result_clear is True and self.sky_clear is False:
            need_update = True
            self.slack_msg("The sky is now clear.")
        elif result_clear is False and self.sky_clear is True:
            need_update = True
            self.slack_msg("The sky is no longer clear.")

        if outside_temp >= HIGH_OUTDOOR_TEMP:
            result_warm = True
        else:
            result_warm = False

        if result_warm is True and self.weather_warm is False:
            need_update = True
            self.slack_msg("It is now warm outside.")
        elif result_warm is False and self.weather_warm is True:
            need_update = True
            self.slack_msg("It is no longer warm outside.")

        if need_update:
            self.sky_clear = result_clear
            self.weather_warm = result_warm
            self.check_fans()

    def find_speed(self):
        # When to keep the fan off
        if self.house_cool and not self.house_asleep:
            return FAN_SPEED[0]

        # When the fan should always be high
        if self.house_downstairs_warm:
            return FAN_SPEED[3]

        if self.direct_sun and self.sky_clear and self.weather_warm:
            return FAN_SPEED[3]

        # Determine variable speed
        speed_adjustment = 0 if self.house_asleep else 1
        calculated_speed = min(max(self.temp_delta - speed_adjustment, 0), 3)
        self.slack_debug(f"Speed adjustment is {speed_adjustment}.  Calculated speed is {calculated_speed}.")
        return FAN_SPEED[calculated_speed]

    def check_fans(self, **kwargs):
        self.slack_debug("Called check_fans.")
        self.check_living_room()
        # self.check_tower()

    def check_living_room(self):
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

    def check_tower(self):
        self.slack_debug("Called check_tower.")
        current_state = self.get_state(self.tower_fan)

        if self.house_upstairs_warm:
            new_state = "on"
        else:
            new_state = "off"

        if current_state == new_state:
            return
        elif new_state == 'on':
            self.turn_on(self.tower_fan)
        else:
            self.turn_off(self.tower_fan)

        self.slack_msg(f"Turning {new_state} tower fan.")

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
