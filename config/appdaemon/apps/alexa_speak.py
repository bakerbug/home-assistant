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
            "media_player.synapse",
        ]
        self.debug_switch = "input_boolean.debug_alexa_speak"
        self.test_switch = "input_boolean.test_alexa_speak"
        try:
            with open(f"{self.config_dir}/secrets.yaml", "r") as secrets_file:
                config_data = yaml.safe_load(secrets_file)
            self.alexa_notify_secret = config_data["notify_me_key"]
            init_msg = "Initialized Alexa Speak."
        except FileNotFoundError:
            self.alexa_notify_secret = None
            init_msg = "###### alexa_speak unable to load secrets.yaml"
            self.log(init_msg)
            self.log(self.config_dir)

        self.test_handler = self.listen_state(self._test_speak, self.test_switch, new="on")
        self.meeting_status = 'switch.shellyplugu1_ebc777'


        self.call_service("notify/slack_assistant", message=init_msg)

        boot_msg = "Home Assistant is now online"
        self.call_service("notify/alexa_media", message=boot_msg, data={"type": "tts"}, target="media_player.computer_room")
        self.bill_location = "sensor.bill_location"

    def alert(self, msg: str, debug_switch: str = None):
        disable = self.get_state("input_boolean.announce_all") == "off"
        if disable:
            return

        alert = f'<audio src="soundbank://soundlibrary/musical/amzn_sfx_electronic_beep_01"/><amazon:emotion name="excited" intensity="low">{msg} </amazon:emotion>'
        self.debug_switch = debug_switch
        target_list = self._select_destinations()
        self.call_service("notify/alexa_media", message=alert, data={"type": "tts", "method": "speak"}, target=target_list)

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
        in_meeting = self.get_state(self.meeting_status) == "on"
        bill_at_work = self.get_state(self.bill_location) == "Synapse Wireless"
        time = self.get_state("sensor.time")
        hour, minute = time.split(":")
        hour = int(hour)

        target_list = deepcopy(self.alexa_list)

        if debug_mode:
            return ["media_player.computer_room"]
        else:
            if bill_in_bed or cricket_in_bed:
                try:
                    target_list.remove("media_player.master_bedroom")
                except ValueError:
                    pass

            if hour >= 20 or hour <= 8:
                # No announcements from 8PM to 8AM.
                try:
                    target_list.remove("media_player.kyle_s_room")
                except ValueError:
                    pass

            if in_meeting:
                try:
                    target_list.remove("media_player.computer_room")
                except ValueError:
                    pass
                try:
                    target_list.remove("media_player.synapse")
                except ValueError:
                    pass

            if not bill_at_work:
                try:
                    target_list.remove("media_player.synapse")
                except ValueError:
                    pass

        return target_list

    def _test_speak(self, entity, attribute, old, new, kwargs):
        self.turn_off(self.test_switch)
        self.notify("This is a test announcement.  There are many like it, but this one is mine.")
        self.respond("This is a test response.  There are many like it, but this one is mine.")
