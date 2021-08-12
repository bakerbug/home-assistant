import appdaemon.plugins.hass.hassapi as hass


class StatusReport(hass.Hass):
    def initialize(self):
        self.entity_list = ("cover.left_bay", "cover.right_bay", "lock.front_door", "lock.back_door")
        self.alexa = self.get_app("alexa_speak")
        self.tesla_bat_lvl = "sensor.meco_battery_sensor"
        self.tesla_charge_rate = "sensor.meco_charging_rate_sensor"
        self.tesla_charge_connected = "binary_sensor.meco_charger_sensor"
        self.tesla_range = "sensor.meco_range_sensor"
        status_switch = self.listen_state(self.run_report, "input_boolean.status_report", new="on")
        self.secure_states = ("closed", "locked")
        self.slack("Initialized Status Report.")

    def run_report(self, entity, attribute, old, new, kwargs):
        self.turn_off("input_boolean.status_report")
        message = self.security_report()
        message = message + self.charge_report()
        self.alexa.respond(message)

    def security_report(self):
        report = ""
        for entity in self.entity_list:
            name = self.friendly_name(entity)
            state = self.get_state(entity)
            if state not in self.secure_states:
                report = report + f"{name} is {state}.  "
        if len(report) == 0:
            report = "The house is secure.  "
        return report

    def charge_report(self):
        try:
            charge_rate = float(self.get_state(self.tesla_charge_rate))
            charge_level = self.get_state(self.tesla_bat_lvl)
            charge_connected = self.get_state(self.tesla_charge_connected) == "on"
            range_mi = int(round(float(self.get_state(self.tesla_range))))
        except (TypeError, ValueError):
            return "Tesla charge status is currently unavailable.  "

        if charge_connected:
            if charge_rate > 0:
                charging_phrase = f"is charging at {charge_rate} miles per hour"
            else:
                charging_phrase = "has finished charging"
        else:
            charging_phrase = "is unplugged"

        return f"Meeco {charging_phrase}, the battery level is {charge_level} percent, and has {range_mi} miles of range.  "

    def send_report(self, report_msg):
        source_alexa = self.get_state("sensor.last_alexa")
        self.call_service("notify/alexa_media", message=report_msg, data={"type": "tts"}, target=source_alexa)

    def slack(self, slack_msg):
        self.call_service("notify/slack_assistant", message=slack_msg)
