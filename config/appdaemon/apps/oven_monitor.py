import appdaemon.plugins.hass.hassapi as hass

# from alexa_speak import AlexaSpeak


class OvenMonitor(hass.Hass):
    def initialize(self):
        # self.oven_handler = self.listen_state(self.oven_check, entity="sensor.range_temperature_measurement")
        self.oven_handler = self.listen_state(self.oven_check, entity="sensor.range_oven_job_state", new="cooking")
        self.alexa = self.get_app("alexa_speak")
        # self.oven_check("bogus", "bogus", "bogus", "bogus", "bogus")

        init_msg = "Initialized Oven Monitor."
        self.call_service("notify/slack_assistant", message=init_msg)

    def oven_check(self, entity, attribute, old, new, kwargs):
        disable = self.get_state("input_boolean.announce_oven_monitor") == "off"
        if disable:
            return

        self.alexa.announce(f"The oven has completed preheating.")
