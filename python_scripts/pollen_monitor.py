import appdaemon.plugins.hass.hassapi as hass
import datetime


class PollenMonitor(hass.Hass):
    def initialize(self):
        self.pollen_warning_level = 8.00
        self.max_increase = 1.00
        self.alert_time = datetime.time(19, 30, 0)
        self.index_today = "sensor.allergy_index_today"
        self.index_tomorrow = "sensor.allergy_index_tomorrow"
        self.alexa = self.get_app("alexa_speak")
        self.debug_switch = "input_boolean.debug_pollen_monitor"
        self.respond_switch = "input_boolean.respond_pollen_monitor"
        self.send_message = self.get_state("input_boolean.notify_pollen_monitor")

        self.turn_off(self.respond_switch)
        self.daily_report = self.run_daily(self.on_schedule, self.alert_time)
        self.response = self.listen_state(self.on_request, self.respond_switch, new="on")

        if self.get_state(self.debug_switch) == "on":

            time, interval, kwargs = self.info_timer(self.daily_report)
            debug_msg = "Daily report: {} every {} seconds.".format(time, interval)
            self.call_service("notify/slack_assistant", message=debug_msg)

            current_time = datetime.datetime.now()
            self.call_service("notify/slack_assistant", message="Initialized at {}".format(current_time))

        init_msg = "Initialized Pollen Monitor."
        self.call_service("notify/slack_assistant", message=init_msg)

    def update_data(self):
        self.today_index = float(self.get_state(self.index_today))
        self.tomorrow_index = float(self.get_state(self.index_tomorrow))
        self.tomorrow_rating = self.get_state(self.index_tomorrow, attribute="rating")
        self.increase_amount = round(self.tomorrow_index - self.today_index, 1)
        self.pollen_state = self.get_state("sensor.allergy_index_tomorrow", attribute="all")

    def on_schedule(self, kwargs):
        self.update_data()
        self.slack_debug(f"Pollen Report? {self.increase_amount} > {self.max_increase} or {self.tomorrow_index} >= {self.pollen_warning_level}")
        if self.increase_amount > self.max_increase or self.tomorrow_index >= self.pollen_warning_level:
            self.report_pollen(False)

    def on_request(self, entity, attribute, old, new, kwargs):
        self.update_data()
        self.report_pollen(True)
        self.turn_off(self.respond_switch)

    def report_pollen(self, requested: bool):
        report_msg = self.generate_report()

        if requested:
            self.alexa.respond(report_msg)
        else:
            report_msg = "Pollen Alert.  " + report_msg
            self.alexa.notify(report_msg)

    def generate_report(self):

        allergens = []

        for key, value in self.pollen_state["attributes"].items():
            if key.startswith("allergen_name"):
                allergens.append(value)

        allergen_count = len(allergens)
        if allergen_count == 1:
            alert_msg = "Tomorrow there will be {} levels of {}.".format(
                self.tomorrow_rating, allergens[0]
            )
        elif allergen_count == 2:
            alert_msg = "Tomorrow there will be {} levels of {} and {}.".format(
                self.tomorrow_rating, allergens[0], allergens[1]
            )
        elif allergen_count > 2:
            alert_msg = "Tomorrow there will be {} levels of {}, {}, and {}.".format(
                self.tomorrow_rating, allergens[0], allergens[1], allergens[2]
            )
        else:
            alert_msg = "The pollen level is {}.".format(self.tomorrow_rating)

        if self.increase_amount > self.max_increase:
            alert_msg = alert_msg + f" The pollen index will increase by {self.increase_amount}."

        return alert_msg

    def slack_debug(self, message):
        debug = self.get_state(self.debug_switch) == "on"
        if debug:
            self.call_service("notify/slack_assistant", message=message)