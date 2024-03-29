import appdaemon.plugins.hass.hassapi as hass
from collections import OrderedDict

FAN_SPEED = OrderedDict()
FAN_SPEED['off'] = 0
FAN_SPEED['low'] = 33
FAN_SPEED['medium'] = 66
FAN_SPEED['high'] = 100

OUTDOOR_TEMPS = {"cool": 60, "warm": 80, "hot": 90}
INDOOR_TEMPS = {"cool": 70, "warm": 75, "hot": 76}
SUN_ELEV_HIGH = 60.00
SUN_ELEV_LOW = 25.00
SUN_AZ_HIGH = 180
WEATHER_SUNNY = ("sunny", "partlycloudy")
WARM_OUTDOOR_TEMP = 80
HOT_OUTDOOR_TEMP = 90
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
        self.weather_temp = None
        self.temp_delta = 0

        self.handle_enable = self.listen_state(self.on_enable_change, entity_id=self.switch_enable)
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
            self.handle_b_bed = self.listen_state(self.on_bed_change, entity_id=self.bed_b)
            self.handle_c_bed = self.listen_state(self.on_bed_change, entity_id=self.bed_c)
            self.handle_sun = self.listen_state(self.on_sun_change, entity_id=self.sun, attribute="elevation")
            self.handle_temp_up = self.listen_state(self.on_temp_change, entity_id=self.temp_up)
            self.handle_temp_down = self.listen_state(self.on_temp_change, entity_id=self.temp_down)
            self.handle_temp_outside = self.listen_state(self.on_weather_change, entity_id=self.weather, attribute="temperature")
            self.handle_weather = self.listen_state(self.on_weather_change, entity_id=self.weather)
            self.check_fans()

            self.slack_msg("Enabled Fan Control.")
        else:
            cancel_handle_list = {self.handle_b_bed, self.handle_c_bed, self.handle_sun, self.handle_temp_up, self.handle_temp_down, self.handle_temp_outside, self.handle_weather}
            for cancel_handle in cancel_handle_list:
                try:
                    self.cancel_listen_state(cancel_handle)
                except (AttributeError, KeyError):
                    pass

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
        need_update = False
        result = False
        sun_elevation = float(self.get_state(self.sun, attribute="elevation"))
        sun_azimuth = float(self.get_state(self.sun, attribute="azimuth"))

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
            self.slack_msg(f"Upstairs is warm at {upstairs_temp} degrees.")
        elif result_up_warm is False and self.house_upstairs_warm is True:
            need_update = True
            self.slack_msg(f"The upstairs is no longer warm at {upstairs_temp} degrees.")

        if result_down_warm is True and self.house_downstairs_warm is False:
            need_update = True
            self.slack_msg(f"The downstairs is warm at {downstairs_temp} degrees.")
        elif result_down_warm is False and self.house_downstairs_warm is True:
            need_update = True
            self.slack_msg(f"The downstairs is no longer warm at {downstairs_temp} degrees.")

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
        result_warm = False
        result_hot = False
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

        if outside_temp >= WARM_OUTDOOR_TEMP:
            result_warm = True
        else:
            result_warm = False

        if outside_temp >= HOT_OUTDOOR_TEMP:
            result_hot = True
        else:
            result_hot = False

        if result_hot is True and self.weather_temp != "hot":
            need_update = True
            self.slack_msg(f"It is hot outside at {outside_temp} degrees.")
        elif result_hot is False and self.weather_temp == "hot":
            self.slack_msg(f"It is no longer hot outside at {outside_temp} degrees.")
            need_update = True
        if result_warm is True and self.weather_temp != "warm":
            need_update = True
            self.slack_msg(f"It is now warm outside at {outside_temp} degrees.")
        elif result_warm is False and self.weather_temp == "warm":
            need_update = True
            self.slack_msg(f"It is no longer warm outside at {outside_temp} degrees.")

        if need_update:
            self.sky_clear = result_clear
            if result_hot:
                self.weather_temp = "hot"
            elif result_warm:
                self.weather_temp = "warm"
            self.check_fans()

    def find_speed(self):
        # When to keep the fan off
        if self.house_cool and not self.house_asleep:
            self.slack_debug(f"find_speed(): House is cool and not asleep.  Speed: {FAN_SPEED['off']}.")
            return FAN_SPEED["off"]

        # When the fan should always be high
        if self.weather_temp == "hot":
            self.slack_debug(f"find_speed(): Weather is hot.  Speed: {FAN_SPEED['high']}.")
            return FAN_SPEED["high"]

        if self.direct_sun and self.sky_clear and self.weather_temp == "warm":
            self.slack_debug(f"find_speed(): Warm, sunny, and clear.  Speed: {FAN_SPEED['high']}.")
            return FAN_SPEED["high"]

        # Determine variable speed
        if self.house_asleep or self.house_downstairs_warm:
            speed_adjustment = 0
        else:
            speed_adjustment = 1

        calculated_speed = min(max(self.temp_delta - speed_adjustment, 0), 3)
        self.slack_debug(f"Speed adjustment is {speed_adjustment}.  Calculated speed is {calculated_speed}.")
        if calculated_speed == 0:
            return FAN_SPEED["off"]
        elif calculated_speed == 1:
            return FAN_SPEED['low']
        elif calculated_speed == 2:
            return FAN_SPEED['medium']
        else:
            return FAN_SPEED['high']

    def check_fans(self, **kwargs):
        self.slack_debug("Called check_fans.")
        self.check_living_room()
        # self.check_tower()

    def check_living_room(self):
        current_speed = int(self.get_state(self.ceiling_fan, attribute="percentage")) or "off"
        self.slack_debug(f"Fan speed is {current_speed}%.")

        new_speed = self.find_speed()
        self.slack_debug(f"Requested fan speed is {new_speed}%.")

        if new_speed == current_speed:
            self.slack_debug("No fan adjustment needed.")
            return
        else:
            self.slack_msg(f"Adjusting fan from {current_speed}% to {new_speed}%.")
            self.call_service("fan/set_percentage", entity_id=self.ceiling_fan, percentage=new_speed)

    def check_tower(self):
        self.slack_debug("Called check_tower.")
        current_state = self.get_state(self.tower_fan)

        if self.house_upstairs_warm:
            new_state = "on"
        else:
            new_state = "off"

        if current_state == new_state:
            return
        elif new_state == "on":
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
