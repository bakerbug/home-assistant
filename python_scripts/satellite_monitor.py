import appdaemon.plugins.hass.hassapi as hass

import datetime
import time
import os
import yaml

import satellites

watch_list = {"International Space Station": 25544}
# watch_list = {"Atlas Centaur 2 R/B": 694}
# watch_list = {"Shenzhou 11": 41868}


class SatMon(hass.Hass):
    def initialize(self):
        update_time = datetime.time(5, 0, 0)
        self.alexa = self.get_app("alexa_speak")
        self.debug_switch = "input_boolean.debug_satellite_monitor"
        self.report_switch = "input_boolean.satellite_report"
        self.weather = "weather.dark_sky"
        self.bad_weather = ("cloudy", "rainy")
        self.turn_off(self.report_switch)

        with open("/home/homeassistant/.homeassistant/secrets.yaml", "r") as secrets_file:
            config_data = yaml.load(secrets_file)
        api_key = config_data["n2yo_key"]
        lat = self.get_state('zone.home', attribute="latitude")
        lon = self.get_state('zone.home', attribute="longitude")
        elevation = 214.9
        self.sat_tracker = satellites.SatData(api_key, lat, lon, elevation)

        self.days = 1
        self.min_visible_seconds = 120
        self.min_magnitude = -1.5
        self.alert_minutes = 10
        self.alert_msg = {}
        self.report_msg = {}

        self.daily_update_handle = self.run_daily(self.update_data, update_time)
        self.report_handle = self.listen_state(self.on_report, self.report_switch, new="on")
        self.alerts_handle = {}

        self.update_data(None)

    def on_alert(self, kwargs):
        weather = self.get_state(self.weather)
        if weather in self.bad_weather:
            return

        self.alexa.announce(self.alert_msg[kwargs["alert_name"]])
        self.slack_debug(self.alert_msg[kwargs["alert_name"]])
        del self.alert_msg[kwargs["alert_name"]]

    def on_report(self, entity, attribute, old, new, kwargs):
        debug = self.get_state(self.debug_switch) == "on"

        for msg in self.report_msg.values():
            self.alexa.respond(msg)
        self.turn_off(self.report_switch)

        if debug:
            for k, v in self.alerts_handle.items():
                self.slack_debug(f"Alert Key: {k} Alert Value: {v}")

    def update_data(self, kwargs):
        report = None
        self.report_msg.clear()

        for sat_name, sat_id in watch_list.items():
            pass_data = self.sat_tracker.get_visual_passes(sat_id, self.days, self.min_visible_seconds)
            brightest_pass = self.find_brightest_pass(pass_data)

            if brightest_pass is not None:
                report = self.get_report_msg(brightest_pass, sat_name)
                self.schedule_alert(brightest_pass, sat_name)
            else:
                report = f"The {sat_name} will not have any significant passes tonight."
            self.report_msg.update({sat_name: report})

    def schedule_alert(self, alert_pass, name):
        start_dt = datetime.datetime.fromtimestamp(alert_pass['startUTC'])
        alert_dt = start_dt - datetime.timedelta(minutes=self.alert_minutes)
        alert_msg = f"The {name} will be visible in {self.alert_minutes} minutes."
        self.alert_msg.update({name: alert_msg})

        try:
            self.cancel_timer(self.alerts_handle[name])
            del self.alerts_handle[name]
        except (AttributeError, KeyError):
            pass

        alert_handle = self.run_at(self.on_alert, alert_dt, alert_name=name)
        self.alerts_handle.update({name: alert_handle})
        self.slack_debug(f"{name} alert scheduled for {alert_dt}")

    def find_brightest_pass(self, pass_data):
        brightest = None

        if pass_data["info"]["passescount"] == 0:
            return None

        for next_pass in pass_data["passes"]:
            # Check time
            pass_ts = next_pass["startUTC"]
            local_dt = datetime.datetime.fromtimestamp(pass_ts)
            self.log(f"Time Check Hour: {local_dt.hour}")

            if local_dt.hour < 12:
                self.log(f"Too early pass at {local_dt.hour} for {next_pass['mag']}")
                continue

            if brightest is None:
                brightest = next_pass
                self.log(f"First candidate at {local_dt.hour} at mag {next_pass['mag']}")
            elif next_pass["mag"] < brightest["mag"]:
                self.log(f"Better candidate at {local_dt.hour} at mag {next_pass['mag']}")
                brightest = next_pass

        if brightest is not None:
            if brightest["mag"] > self.min_magnitude:
                self.log("Best candidate was too dim.")
                self.slack_debug(f"Brightest pass was {brightest['mag']} but over the limit of {self.min_magnitude}.")
                return None

        self.log(f"Best candidate is {brightest['mag']}")
        return brightest

    def get_report_msg(self, next_pass, sat_name):
        sat_name = sat_name.title()
        start_time = self.format_date(next_pass["startUTC"])
        start_dir = self.format_direction(next_pass["startAzCompass"])
        end_dir = self.format_direction(next_pass["endAzCompass"])
        duration = next_pass["duration"]
        mag = next_pass["mag"]
        msg = f"The {sat_name} will be passing over on {start_time}.  It will be appearing in the {start_dir} and travel toward the {end_dir} being visible for {duration} seconds with a magnitude of {mag}."

        return msg

    def slack_debug(self, message):
        debug = self.get_state(self.debug_switch) == "on"
        if debug:
            self.call_service("notify/slack_assistant", message=message)

    @staticmethod
    def format_date(ts):
        local_ts = time.localtime(ts)
        if os.name == "nt":
            format_string = "%A, %B %#e at %#I:%M %p"
        else:
            format_string = "%A, %B %-d at %-I:%M %p"
        return time.strftime(format_string, local_ts)

    @staticmethod
    def format_direction(abv_dir):
        if abv_dir == "N":
            direction = "north"
        elif abv_dir == "NNE":
            direction = "north-north-east"
        elif abv_dir == "NE":
            direction = "north-east"
        elif abv_dir == "ENE":
            direction = "east-north-east"
        elif abv_dir == "E":
            direction = "east"
        elif abv_dir == "ESE":
            direction = "east-south-east"
        elif abv_dir == "SE":
            direction = "south-east"
        elif abv_dir == "SSE":
            direction = "south-south-east"
        elif abv_dir == "S":
            direction = "south"
        elif abv_dir == "SSW":
            direction = "south-south-west"
        elif abv_dir == "SW":
            direction = "south-west"
        elif abv_dir == "WSW":
            direction = "west-south-west"
        elif abv_dir == "W":
            direction = "west"
        elif abv_dir == "WNW":
            direction = "west-north-west"
        elif abv_dir == "NW":
            direction = "north-west"
        elif abv_dir == "NNW":
            direction = "north-north-west"
        else:
            direction = "unknown"

        return direction
