import appdaemon.plugins.hass.hassapi as hass

class StatusReport(hass.Hass):

    def initialize(self):
        self.entity_list = ("cover.left_bay", "cover.right_bay", "lock.front_door")
        self.alexa_list = ['media_player.master_bedroom']
        status_switch = self.listen_state(self.run_report, "input_boolean.status_report", new="on")
        self.slack("Initialized Status Report.")

    def run_report(self, entity, attribute, old, new, kwargs):
        message = self.generate_report()
        self.send_report(message)

        self.turn_off("input_boolean.status_report")

    def generate_report(self):
        report = ""
        for entity in self.entity_list:
            name = self.friendly_name(entity)
            state = self.get_state(entity)
            report = report + f"{name} is {state}. "
        return report

    def send_report(self, report_msg):
        self.call_service("notify/alexa_media", message=report_msg, data={"type": "tts"},
            target=self.alexa_list)

    def slack(self, slack_msg):
        self.call_service("notify/slack_assistant", message=slack_msg)
