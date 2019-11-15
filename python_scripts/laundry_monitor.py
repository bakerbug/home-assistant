import appdaemon.plugins.hass.hassapi as hass
import datetime

class LaundryMonitor(hass.Hass):

    def initialize(self):
        clock = datetime.time(0, 0, 0)
        every_minute = self.run_minutely(self.check_power, clock)
        self.alexa_list = ['media_player.kitchen', 'media_player.computer_room', 'media_player.master_bedroom']
        self.washer_on = False
        self.power_limit = 10
        self.wait_minutes = 5
        self.ticks = 0

        init_msg = "Initialized Laundry Monitor."
        self.call_service("notify/slack_assistant", message=init_msg)

    def check_power(self, args):
        self.DEBUG = self.get_state("input_boolean.debug_laundry") == "on"
        self.power_level = float(self.get_state("sensor.washing_machine_power"))

        if self.washer_on:
            if self.power_level < self.power_limit:
                if self.ticks >= self.wait_minutes:
                    self.alexa_notify("The laundry has completed.")
                    self.washer_on = False
                    self.ticks = 0
                else:
                    self.ticks += 1
        elif self.power_level > self.power_limit:
            self.washer_on = True

        self.slack_debug(f'Laundry ticks: {self.ticks}')

    def alexa_notify(self, message):
        if self.DEBUG:
            target_list = 'media_player.computer_room'
        else:
            target_list = self.alexa_list

        self.call_service('notify/alexa_media', message=message, data={"type": "tts"},
                          target=target_list)

    def slack_debug(self, message):
        debug = self.get_state("input_boolean.debug_laundry") == "on"
        if debug:
            self.call_service("notify/slack_assistant", message=message)
