import appdaemon.plugins.hass.hassapi as hass


class AlexaSpeak(hass.Hass):

    def initialize(self):
        #self.alexa_list = ["media_player.kitchen", "media_player.computer_room", "media_player.master_bedroom", "media_player.kyle_s_room"]

        # Don't play in Kyle's room until quiet hours implemented.
        self.alexa_list = ["media_player.kitchen", "media_player.computer_room", "media_player.master_bedroom"]


        init_msg = "Initialized Alexa Speak."
        self.call_service("notify/slack_assistant", message=init_msg)

    def announce(self, msg: str):
        disable = self.get_state('input_boolean.announce_all') == 'off'
        if disable:
            return

        target_list = self._select_destinations()
        self.call_service("notify/alexa_media", message=msg, data={"type": "tts"}, target=target_list)

    def respond(self, msg: str):
        source_alexa = self.get_state("sensor.last_alexa")
        self.call_service("notify/alexa_media", message=msg, data={"type": "tts"},
                          target=source_alexa)

    def _select_destinations(self):
        debug_mode = self.get_state('input_boolean.debug_alexa_speak') == 'on'
        cricket_in_bed = self.get_state("binary_sensor.sleepnumber_bill_cricket_is_in_bed") == "on"
        target_list = self.alexa_list

        if debug_mode:
            return ["media_player.computer_room",]
        else:
            if cricket_in_bed:
                target_list.remove("media_player.master_bedroom")

            return target_list
