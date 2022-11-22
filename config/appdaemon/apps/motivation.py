import logging

import appdaemon.plugins.hass.hassapi as hass
import requests
import json

API = "https://www.affirmations.dev"
trigger_switch = "input_boolean.motivation_switch"

class Motivator(hass.Hass):
    def initialize(self):
        self.alexa = self.get_app("alexa_speak")

        self.msg = "You can do it!"
        self.fetch_motivation()
        logging.error(self.msg)
        self.slack_msg(self.msg)
        self.response_handle = self.listen_state(self.encourage, trigger_switch, new="on")


    def fetch_motivation(self):
        response = requests.get(API, verify=False)
        if response.status_code == requests.codes.ok:
            data = json.loads(response.content)
            self.msg = data["affirmation"]
        else:
            self.msg = "Yeah, that didn't go so well."

    def encourage(self, entity, attribute, old, new, kwargs):
        self.turn_off(trigger_switch)
        self.alexa.respond(self.msg)
        self.fetch_motivation()

    def slack_debug(self, message):
        debug = self.get_state(self.debug_switch) == "on"
        if debug:
            self.call_service("notify/slack_assistant", message=message)

    def slack_msg(self, message):
        self.call_service("notify/slack_assistant", message=message)
