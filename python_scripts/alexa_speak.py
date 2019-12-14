import appdaemon.plugins.hass.hassapi as hass
import json
import requests
import yaml


class AlexaSpeak(hass.Hass):

    def initialize(self):
        #self.alexa_list = ["media_player.kitchen", "media_player.computer_room", "media_player.master_bedroom", "media_player.kyle_s_room"]

        # Don't play in Kyle's room until quiet hours implemented.
        self.alexa_list = ["media_player.kitchen", "media_player.computer_room", "media_player.master_bedroom"]
        self.debug_switch = None

        with open('/home/homeassistant/.homeassistant/secrets.yaml', 'r') as secrets_file:
            config_data = yaml.load(secrets_file)
        self.alexa_notify_secret = config_data['notify_me_key']


        init_msg = "Initialized Alexa Speak."
        self.call_service("notify/slack_assistant", message=init_msg)

    def announce(self, msg: str, debug_switch: str = None):
        disable = self.get_state('input_boolean.announce_all') == 'off'
        if disable:
            return

        self.debug_switch = debug_switch
        target_list = self._select_destinations()
        self.call_service("notify/alexa_media", message=msg, data={"type": "tts"}, target=target_list)

    def notify(self, msg: str, debug_switch: str = None):
        body = json.dumps({'notification': msg, 'accessCode': self.alexa_notify_secret})
        requests.post(url="https://api.notifymyecho.com/v1/NotifyMe", data=body)

    def respond(self, msg: str, debug_switch: str = None):
        source_alexa = self.get_state("sensor.last_alexa")
        self.call_service("notify/alexa_media", message=msg, data={"type": "tts"},
                          target=source_alexa)

    def _select_destinations(self):
        debug_mode = self.get_state(self.debug_switch) == 'on'
        cricket_in_bed = self.get_state("binary_sensor.sleepnumber_bill_cricket_is_in_bed") == "on"
        target_list = self.alexa_list

        if debug_mode:
            return ["media_player.computer_room",]
        else:
            if cricket_in_bed:
                target_list.remove("media_player.master_bedroom")

            return target_list
