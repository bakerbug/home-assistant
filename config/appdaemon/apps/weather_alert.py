import appdaemon.plugins.hass.hassapi as hass

import inflect


class AlertData:
    def __init__(self, nws_alert):
        self.id = nws_alert["id"]
        self.type = nws_alert["event"]
        self.details = nws_alert["description"]
        self.expiration = nws_alert["expires"]

        self.announced = False


class AlertList:
    def __init__(self):
        self.alerts = []

    def update_data(self, nws_data):
        for alert_data in nws_data:
            if self.alert_is_new(alert_data["id"]):
                self.alerts.append(AlertData(alert_data))

    def alert_is_new(self, new_id) -> bool:
        for alert in self.alerts:
            if new_id == alert.id:
                return False
        return True

    def alert_count_total(self):
        return len(self.alerts)

    def alert_count_new(self):
        if self.alert_count_total() == 0:
            return 0

        new_count = 0
        for alert in self.alerts:
            if alert.announced is False:
                new_count += 1
        return new_count

    def alert_count_old(self):
        if self.alert_count_total() == 0:
            return 0

        old_count = 0
        for alert in self.alerts:
            if alert.announced is True:
                old_count += 1
        return old_count

    def announce_new_alerts(self):
        for alert in self.alerts:
            if alert.announced is False:
                self.send_alert (alert)

    def send_alert(self, announcement):
        # This doesn't belong in the AlertList.  Move to WeatherAlert class.
        event = announcement["event"]
        event_msg = f"The National Weather Service has issued a {event}."
        return event_msg


    def generate_report(self):
        current_count = self.alert_count()

        if current_count == 0:
            report = "There are no active weather alerts at this time.  "
        elif current_count == 1:
            report = "There is one active alert.  "
        else:
            report = f"There are {current_count} active alerts.  "

        return report


class WeatherAlert(hass.Hass):
    def initialize(self):
        self.alexa = self.get_app("alexa_speak")
        self.alert_sensor = "sensor.madison"
        self.report_requested = "input_boolean.weather_alert_details"
        self.alert_handle = self.listen_state(self.on_alert_change, self.alert_sensor)
        self.details_handle = self.listen_state(self.on_report_requested, self.report_requested, new="on")
        self.debug_switch = "input_boolean.debug_weather_alert"


        self.weather_alerts = AlertList()
        self.log('AlertList initialized.')

        self.slack_msg("Initialized Weather Alert.")

        if self.get_state(self.debug_switch) == "on":
            self.on_alert_change("bogus", "bogus", "bogus", "bogus", "bogus")

        if int(self.get_state(self.alert_sensor)) > 0:
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

        self.log(f"Preparing to update data.")
        self.weather_alerts.update_data(self.get_state(self.alert_sensor, attribute="alerts"))


    def on_report_requested(self, entity, attribute, old, new, kwargs):
        self.turn_off(self.report_requested)
        try:
            alert_count = int(self.get_state(self.alert_sensor))
        except ValueError:
            self.alexa.respond("The weather service is unavailable at this time.")
            return

        self.slack_debug(f"Alert count is {alert_count}.")

        # if alert_count == 0:
        #     self.alexa.respond("There are no active weather alerts at this time.")
        #     return
        # if alert_count == 1:
        #     detail_msg = "There is one active alert.  "
        # else:
        #     detail_msg = f"There are {alert_count} active alerts.  "

        detail_msg = self.new_list.generate_report()

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
            self.log("Yes, done parsing alert.")
            return None
        self.log("No, continue parsing")

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
