import appdaemon.plugins.hass.hassapi as hass
import datetime


class PollenMonitor(hass.Hass):
    def initialize(self):
        self.pollen_warning_level = 8.00
        self.alert_time = datetime.time(19, 30, 0)
        #self.alert_time = datetime.time(0, 30, 0)  # Hack to fix issue getting timezone correct
        self.alexa = self.get_app("alexa_speak")
        self.debug_switch = "input_boolean.debug_pollen_monitor"
        self.respond_switch = "input_boolean.respond_pollen_monitor"
        self.send_message = self.get_state("input_boolean.notify_pollen_monitor")

        self.daily_report = self.run_daily(self.on_schedule, self.alert_time)
        self.response = self.listen_state(self.on_request, self.respond_switch, new="on")

        if self.get_state(self.debug_switch) == "on":

            self.call_service("notify/slack_assistant", message="Initializing Pollen Report")
            time, interval, kwargs = self.info_timer(self.daily_report)
            debug_msg = "Daily report: {} every {} seconds.".format(time, interval)
            self.call_service("notify/slack_assistant", message=debug_msg)

            current_time = datetime.datetime.now()
            self.call_service("notify/slack_assistant", message="Initialized at {}".format(current_time))

        self.report_pollen(True)

        init_msg = "Initialized Pollen Monitor."
        self.call_service("notify/slack_assistant", message=init_msg)

    def on_schedule(self, kwargs):
        self.slack_debug("Pollen Monitor running scheduled alert.")
        notify = self.get_state("input_boolean.notify_pollen_monitor") == "on"
        if notify:
            self.report_pollen(False)

    def on_request(self, entity, attribute, old, new, kwargs):
        self.report_pollen(True)
        self.turn_off(self.respond_switch)

    def report_pollen(self, requested: bool):
        debug = self.get_state(self.debug_switch) == "on"
        self.pollen_index = self.get_state("sensor.allergy_index_tomorrow")
        self.pollen_rating = self.get_state("sensor.allergy_index_tomorrow", attribute="rating")
        alert_msg = self.generate_alert_message()

        if debug:
            self.alexa.announce(alert_msg, self.debug_switch)
        if requested:
            self.alexa.respond(alert_msg)
        elif float(self.pollen_index) >= self.pollen_warning_level:
            alert_msg = "Pollen Alert.  " + alert_msg
            self.alexa.notify(alert_msg)

    def generate_alert_message(self):
        pollen_state = self.get_state("sensor.allergy_index_tomorrow", attribute="all")
        allergens = []

        for key, value in pollen_state["attributes"].items():
            if key.startswith("allergen_name"):
                allergens.append(value)

        allergen_count = len(allergens)
        if allergen_count == 1:
            alert_msg = "Tomorrow there will be {} levels of {}.".format(
                self.pollen_rating, allergens[0]
            )
        elif allergen_count == 2:
            alert_msg = "Tomorrow there will be {} levels of {} and {}.".format(
                self.pollen_rating, allergens[0], allergens[1]
            )
        elif allergen_count > 2:
            alert_msg = "Tomorrow there will be {} levels of {}, {}, and {}.".format(
                self.pollen_rating, allergens[0], allergens[1], allergens[2]
            )
        else:
            alert_msg = "The pollen level is {}.".format(self.pollen_rating)

        return alert_msg

    def slack_debug(self, message):
        debug = self.get_state(self.debug_switch) == "on"
        if debug:
            self.call_service("notify/slack_assistant", message=message)