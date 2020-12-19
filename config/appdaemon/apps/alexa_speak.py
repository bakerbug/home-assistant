import appdaemon.plugins.hass.hassapi as hass
import json
import requests
import yaml

from copy import deepcopy


class AlexaSpeak(hass.Hass):
    def initialize(self):
        self.alexa_list = [
            "media_player.kitchen",
            "media_player.computer_room",
            "media_player.master_bedroom",
            "media_player.kyle_s_room",
            "media_player.echo_auto_camry",
            "media_player.extra",
        ]
        self.debug_switch = None
        try:
            with open(f"{self.config_dir}/secrets.yaml", "r") as secrets_file:
                config_data = yaml.safe_load(secrets_file)
            self.alexa_notify_secret = config_data["notify_me_key"]
        except FileNotFoundError:
            self.alexa_notify_secret = None
            self.log("######")
            self.log(self.config_dir)

        init_msg = "Initialized Alexa Speak."
        self.call_service("notify/slack_assistant", message=init_msg)

        boot_msg = "Home Assistant is now online"
        self.call_service("notify/alexa_media", message=boot_msg, data={"type": "tts"}, target="media_player.computer_room")

    def announce(self, msg: str, debug_switch: str = None):
        disable = self.get_state("input_boolean.announce_all") == "off"
        if disable:
            return

        self.debug_switch = debug_switch
        target_list = self._select_destinations()
        self.call_service("notify/alexa_media", message=msg, data={"type": "tts"}, target=target_list)

    def notify(self, msg: str, debug_switch: str = None):
        body = json.dumps({"notification": msg, "accessCode": self.alexa_notify_secret})
        requests.post(url="https://api.notifymyecho.com/v1/NotifyMe", data=body)

    def respond(self, msg: str, debug_switch: str = None):
        source_alexa = self.get_state("sensor.last_alexa")
        self.call_service("notify/alexa_media", message=msg, data={"type": "tts"}, target=source_alexa)

    def debug(self, msg: str):
        self.call_service("notify/alexa_media", message=msg, data={"type": "tts"}, target="media_player.computer_room")

    def _select_destinations(self):
        debug_mode = self.get_state(self.debug_switch) == "on"
        bill_in_bed = self.get_state("binary_sensor.sleepnumber_bill_bill_is_in_bed") == "on"
        cricket_in_bed = self.get_state("binary_sensor.sleepnumber_bill_cricket_is_in_bed") == "on"
        time = self.get_state("sensor.time")
        hour, minute = time.split(":")
        hour = int(hour)

        target_list = deepcopy(self.alexa_list)

        if debug_mode:
            return [
                "media_player.computer_room",
            ]
        else:
            if bill_in_bed or cricket_in_bed:
                target_list.remove("media_player.master_bedroom")

            if hour >= 20 or hour <= 8:
                # No announcements from 8PM to 8AM.
                target_list.remove("media_player.kyle_s_room")

        return target_list
