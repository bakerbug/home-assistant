import appdaemon.plugins.hass.hassapi as hass

import inflect


class WeatherAlert(hass.Hass):
    def initialize(self):
        self.alexa = self.get_app("alexa_speak")
        # self.alert_sensor = "sensor.ilz014"
        # self.alert_sensor = "sensor.north_douglas_county_below_6000_feet_denver_west_adams_and_arapahoe_counties_east_broomfield_county"
        self.alert_sensor = "sensor.madison"
        self.alert_detail = "input_boolean.weather_alert_details"
        self.alerts = {}
        self.alert_ids = []
        self.alert_events = []
        self.alert_descriptions = []
        self.alert_announced = []
        self.alert_handle = self.listen_state(self.on_alert_change, self.alert_sensor)
        self.details_handle = self.listen_state(self.on_alert_details, self.alert_detail, new="on")
        self.debug_switch = "input_boolean.debug_weather_alert"
        self.slack_msg("Initialized Weather Alert.")

        if self.get_state(self.debug_switch) == "on":
            self.on_alert_change("bogus", "bogus", "bogus", "bogus", "bogus")

    def on_alert_change(self, entity, attribute, old, new, kwargs):
        try:
            alert_count = int(self.get_state(self.alert_sensor))
        except ValueError:
            self.log("Weather service unavailable.")
            return

        if alert_count == 0:
            self.alert_ids.clear()
            self.log("All weather alerts have cleared.")
            return

        full_data = self.get_state(self.alert_sensor, attribute="alerts")
        for alert_data in full_data:
            alert_msg = self.parse_alert(alert_data)
            if alert_msg is not None:
                self.alexa.announce(alert_msg, self.debug_switch)
                self.slack_msg(alert_msg)


        self.log(self.alert_ids)

    def on_alert_details(self, entity, attribute, old, new, kwargs):
        self.turn_off(self.alert_detail)
        try:
            alert_count = int(self.get_state(self.alert_sensor))
        except ValueError:
            self.alexa.respond("The weather service is unavailable at this time.")
            return

        self.slack_debug(f"Alert count is {alert_count}.")

        if alert_count == 0:
            self.alexa.respond("There are no active weather alerts at this time.")
            return
        if alert_count == 1:
            detail_msg = "There is one active alert.  "
        else:
            detail_msg = f"There are {alert_count} active alerts.  "

        speak = inflect.engine()
        alert_index = 1
        full_data = self.get_state(self.alert_sensor, attribute="alerts")
        for alert_data in full_data:
            if alert_count > 1:
                detail_msg = detail_msg + f"  {speak.ordinal(alert_index)} alert:  "
                alert_index += 1

            alert_description = alert_data["description"]
            if alert_description is None:
                alert_description = "The weather alert description is unavailable.  "

            detail_msg = detail_msg + alert_description

        self.alexa.respond(detail_msg)
        self.slack_debug(detail_msg)

    def parse_alert(self, data):
        self.log(f'Is {data["id"]} in {self.alert_ids}?')
        if data["id"] in self.alert_ids:
            return None

        self.alert_ids.append(data["id"])
        event = data["event"]
        self.alert_events.append(event)
        self.alert_descriptions.append(data["description"])
        self.alert_announced.append(False)
        event_msg = f"The National Weather Service has issued a {event}."

        return event_msg

    def slack_debug(self, message):
        debug = self.get_state(self.debug_switch) == "on"
        if debug:
            self.call_service("notify/slack_assistant", message=message)

    def slack_msg(self, message):
        self.call_service("notify/slack_assistant", message=message)
