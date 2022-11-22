import appdaemon.plugins.hass.hassapi as hass


class StatusReport(hass.Hass):
    def initialize(self):
        self.entity_list = ("cover.left_bay", "cover.right_bay", "lock.front_door", "lock.back_door")
        self.alexa = self.get_app("alexa_speak")
        self.motion_backyard = "binary_sensor.backyard_cam_motion"
        self.motion_driveway = "binary_sensor.driveway_cam_motion"
        self.motion_frontdoor = "binary_sensor.front_door_cam_motion"
        self.motion_count_backyard = 0
        self.motion_count_driveway = 0
        self.motion_count_frontdoor = 0
        self.tesla_bat_lvl = "sensor.meco_battery"
        self.tesla_charge_rate = "sensor.meco_charging_rate"
        self.tesla_charge_connected = "binary_sensor.meco_charger"
        self.tesla_charge_limit = "number.meco_charge_limit"
        self.tesla_range = "sensor.meco_range"
        self.tesla_update = "update.meco_software_update"
        self.handler_run_report = self.listen_state(self.run_report, "input_boolean.status_report", new="on")
        self.handler_on_new_night = self.listen_state(self.on_new_night, "sun.sun", new="below_horizon")
        self.handler_backyard_motion = self.listen_state(self.on_night_motion, self.motion_backyard, new="on")
        self.handler_driveway_motion = self.listen_state(self.on_night_motion, self.motion_driveway, new="on")
        self.handler_frontdoor_motion = self.listen_state(self.on_night_motion, self.motion_frontdoor, new="on")

        self.secure_states = ("closed", "locked")
        self.slack("Initialized Status Report.")

    def on_new_night(self, entity, attribute, old, new, kwargs):
        self.motion_count_backyard = 0
        self.motion_count_driveway = 0
        self.motion_count_frontdoor = 0

    def on_night_motion(self, entity, attribute, old, new, kwargs):
        is_night = self.get_state("sun.sun") == "below_horizon"

        if not is_night:
            return

        if entity == self.motion_backyard:
            self.motion_count_backyard += 1
        elif entity == self.motion_driveway:
            self.motion_count_driveway += 1
        elif entity == self.motion_frontdoor:
            self.motion_count_frontdoor += 1

    def run_report(self, entity, attribute, old, new, kwargs):
        self.turn_off("input_boolean.status_report")
        message = self.security_report()
        message = message + self.charge_report()
        message = message + self.motion_report()
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
            charge_level = int(self.get_state(self.tesla_bat_lvl))
            charge_connected = self.get_state(self.tesla_charge_connected) == "on"
            range_mi = int(round(float(self.get_state(self.tesla_range))))
            charge_goal = int(round(float(self.get_state(self.tesla_charge_limit))))
            update_available = self.get_state(self.tesla_update) == "on"
        except (TypeError, ValueError):
            return "Tesla status is currently unavailable.  "

        if charge_connected:
            if charge_rate > 0:
                charging_phrase = f"is charging at {charge_rate} miles per hour"
            elif charge_level < charge_goal:
                charging_phrase = "is waiting to charge "
            else:
                charging_phrase = "has finished charging"
        else:
            charging_phrase = "is unplugged"

        if update_available:
            msg = f"Meeco has a software update available, {charging_phrase}, the battery level is {charge_level} percent, and has {range_mi} miles of range.  "
        else:
            msg = f"Meeco {charging_phrase}, the battery level is {charge_level} percent, and has {range_mi} miles of range.  "

        return msg

    def motion_report(self):
        is_day = self.get_state("sun.sun") == "above_horizon"

        if is_day:
            report = "Last night there were "
        else:
            report = "Tonight there have been "

        if self.motion_count_backyard + self.motion_count_driveway + self.motion_count_frontdoor == 0:
            report = report + "no motion events.  "
            return report

        if self.motion_count_backyard > 0:
            report = report + f"{self.motion_count_backyard} backyard, "
        if self.motion_count_driveway > 0:
            report = report + f"{self.motion_count_driveway} driveway, "
        if self.motion_count_frontdoor > 0:
            report = report + f"{self.motion_count_frontdoor} front door, "

        report = report + "events.  "

        return report

    def send_report(self, report_msg):
        source_alexa = self.get_state("sensor.last_alexa")
        self.call_service("notify/alexa_media", message=report_msg, data={"type": "tts"}, target=source_alexa)

    def slack(self, slack_msg):
        self.call_service("notify/slack_assistant", message=slack_msg)
