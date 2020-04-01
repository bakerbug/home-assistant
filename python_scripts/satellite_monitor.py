import appdaemon.plugins.hass.hassapi as hass

import datetime
import time
import os
import yaml
import satellites

track_list = (
    {'name': "International Space Station", 'id': 25544, 'mag_limit': -1.5},
    {'name': "Hubble Space Telescope", 'id': 20580, 'mag_limit': 3.0},
)

### Previously tracked:
#  {'name': "Atlas Centaur 2 upper stage", 'id': 694, 'mag_limit': 2.0},
#  {'name': "Shenzhou 11", 'id': 41868, 'mag_limit': 2.0},

class SatMon(hass.Hass):
    def initialize(self):
        update_time = datetime.time(5, 0, 0)
        self.alexa = self.get_app("alexa_speak")
        self.debug_switch = "input_boolean.debug_satellite_monitor"
        self.report_switch = "input_boolean.satellite_report"
        self.weather = "weather.dark_sky"
        self.bad_weather = ("cloudy", "rainy", "partlycloudy")
        self.turn_off(self.report_switch)
        self.query_complete = False

        with open("/home/homeassistant/.homeassistant/secrets.yaml", "r") as secrets_file:
            config_data = yaml.safe_load(secrets_file)
        api_key = config_data["n2yo_key"]
        lat = self.get_state('zone.home', attribute="latitude")
        lon = self.get_state('zone.home', attribute="longitude")
        elevation = 214.9
        self.sat_tracker = satellites.SatData(api_key, lat, lon, elevation)

        self.days = 1
        self.min_visible_seconds = 120
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
        self.slack_msg(self.report_msg[kwargs["alert_name"]])
        del self.alert_msg[kwargs["alert_name"]]

    def on_report(self, entity, attribute, old, new, kwargs):
        self.log('Processing request for satellite report.')
        msg = ''
        found_one = False
        self.turn_off(self.report_switch)
        debug = self.get_state(self.debug_switch) == "on"

        for report in self.report_msg.values():
            if report is not None:
                found_one = True
                msg = msg + report

        if not found_one:
            msg = "There are no satellites visible tonight."

        if self.query_complete is False:
            msg = "Please ask again.  I'm updating the satellite data."

        self.alexa.respond(msg)

    def update_data(self, kwargs):
        self.query_complete = False
        report = None
        self.report_msg.clear()

        for satellite in track_list:
            pass_data = self.sat_tracker.get_visual_passes(satellite['id'], self.days, self.min_visible_seconds)
            self.log(f"Processing data for {satellite['name']}.")
            brightest_pass = self.find_brightest_pass(pass_data)

            if brightest_pass is not None:
                report, alert = self.get_report_msg(brightest_pass, satellite['name'], satellite['mag_limit'])
                if alert:
                    self.schedule_alert(brightest_pass, satellite['name'], report)

                self.report_msg.update({satellite['name']: report})

        self.query_complete = True

    def schedule_alert(self, alert_pass, name, msg):
        start_dt = datetime.datetime.fromtimestamp(alert_pass['startUTC'])
        alert_dt = start_dt - datetime.timedelta(minutes=self.alert_minutes)
        alert_msg = f"The {name} will be visible in {self.alert_minutes} minutes.  "
        text_msg = f"The {name} will be visible at {start_dt} tonight."
        self.alert_msg.update({name: alert_msg})

        try:
            self.cancel_timer(self.alerts_handle[name])
            del self.alerts_handle[name]
        except (AttributeError, KeyError):
            pass

        alert_handle = self.run_at(self.on_alert, alert_dt, alert_name=name)
        self.alerts_handle.update({name: alert_handle})
        self.slack_debug(f"{name} alert scheduled for {alert_dt}")
        self.slack_msg(text_msg)

    def find_brightest_pass(self, pass_data):
        brightest = None

        try:
            if pass_data["info"]["passescount"] == 0:
                self.log("No visible passes.")
                return None
        except KeyError:
            self.log("No pass data available.")
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

        return brightest

    def get_report_msg(self, next_pass, sat_name, min_magnitude):
        sat_name = sat_name.title()
        start_time = self.format_date(next_pass["startUTC"])
        start_dir = self.format_direction(next_pass["startAzCompass"])
        end_dir = self.format_direction(next_pass["endAzCompass"])
        duration = next_pass["duration"]
        mag = next_pass["mag"]
        set_alert = False

        if next_pass["mag"] > min_magnitude:
            msg = f"The {sat_name} will pass over tonight at {start_time} but will not be very bright.  It's magnitude will be {next_pass['mag']}.  "

        else:
            msg = f"The {sat_name} will be passing over tonight at {start_time}.  It will be appearing in the {start_dir} and travel toward the {end_dir} being visible for {duration} seconds with a magnitude of {mag}.  "
            set_alert = True

        return msg, set_alert

    def slack_debug(self, message):
        debug = self.get_state(self.debug_switch) == "on"
        if debug:
            self.call_service("notify/slack_assistant", message=message)

    def slack_msg(self, message):
        self.call_service("notify/slack_assistant", message=message)

    @staticmethod
    def format_date(ts):
        local_ts = time.localtime(ts)
        if os.name == "nt":
            format_string = "%A, %B %#e at %#I:%M %p"  # Monday February 17th at 4:37 PM
            format_string = "%#I:%M %p"
        else:
            format_string = "%A, %B %-d at %-I:%M %p"  # Monday February 17th at 4:37 PM
            format_string = "%-I:%M %p"
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
