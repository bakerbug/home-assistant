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
        try:
            self.today_index = float(self.get_state(self.index_today))
            self.tomorrow_index = float(self.get_state(self.index_tomorrow))
        except ValueError:
            self.today_index = 0.0
            self.tomorrow_index = 0.0

        self.today_rating = self.get_state(self.index_today, attribute="rating")
        self.tomorrow_rating = self.get_state(self.index_tomorrow, attribute="rating")
        self.index_change = round(self.tomorrow_index - self.today_index, 1)
        self.pollen_state_tomorrow = self.get_state(self.index_tomorrow, attribute="all")
        self.pollen_state_today = self.get_state(self.index_today, attribute="all")

    def on_schedule(self, kwargs):
        self.update_data()
        self.slack_debug(f"Pollen Report? {self.index_change} > {self.max_increase} or {self.tomorrow_index} >= {self.pollen_warning_level}")
        if self.index_change > self.max_increase or self.tomorrow_index >= self.pollen_warning_level:
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
        if self.get_state(self.index_today) == "unknown":
            return "Pollen data is currently unavailable."

        allergens_today = self.get_allergen_stanza(self.pollen_state_today)
        allergens_tomorrow = self.get_allergen_stanza(self.pollen_state_tomorrow)

        alert_msg = f"Today, there is a {self.today_rating} level of {allergens_today}.  "

        if self.index_change > 0:
            direction = f"increase by {abs(self.index_change)} "
        elif self.index_change < 0:
            direction = f"decrease by {abs(self.index_change)} "
        else:
            direction = "remain the same "

        alert_msg = alert_msg + f"Tomorrow, the pollen index will {direction} "
        alert_msg = alert_msg + f"with a {self.tomorrow_rating} level of {allergens_tomorrow}."

        return alert_msg

    @staticmethod
    def get_allergen_stanza(pollen_state):
        allergen_list = []
        for key, value in pollen_state["attributes"].items():
            if key.startswith("allergen_name"):
                allergen_list.append(value)

        allergen_count = len(allergen_list)

        if allergen_count == 1:
            response = f"{allergen_list[0]}."
        elif allergen_count == 2:
            response = f"{allergen_list[0]} and {allergen_list[1]}."
        elif allergen_count == 3:
            response = f"{allergen_list[0]}, {allergen_list[1]}, and {allergen_list[2]}."
        else:
            response = f"{allergen_count} types of pollen."

        return response

    def slack_debug(self, message):
        debug = self.get_state(self.debug_switch) == "on"
        if debug:
            self.call_service("notify/slack_assistant", message=message)
