import appdaemon.plugins.hass.hassapi as hass


class StatusReport(hass.Hass):
    def initialize(self):
        self.entity_list = ("cover.left_bay", "cover.right_bay", "lock.front_door")
        self.alexa = self.get_app("alexa_speak")
        status_switch = self.listen_state(self.run_report, "input_boolean.status_report", new="on")
        self.insecure_states = ("open", "unlocked")
        self.slack("Initialized Status Report.")

    def run_report(self, entity, attribute, old, new, kwargs):
        message = self.generate_report()
        self.alexa.respond(message)

        self.turn_off("input_boolean.status_report")

    def generate_report(self):
        report = ""
        for entity in self.entity_list:
            name = self.friendly_name(entity)
            state = self.get_state(entity)
            if state in self.insecure_states:
                report = report + f"{name} is {state}. "
        if len(report) == 0:
            report = "The house is secure."
        return report

    def send_report(self, report_msg):
        source_alexa = self.get_state("sensor.last_alexa")
        self.call_service("notify/alexa_media", message=report_msg, data={"type": "tts"}, target=source_alexa)

    def slack(self, slack_msg):
        self.call_service("notify/slack_assistant", message=slack_msg)
