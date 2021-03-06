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
        # oven_on = self.get_state("sensor.range_oven_job_state") == "cooking"
        # if not oven_on:
        #    return

        # current_temp = int(float(self.get_state("sensor.range_temperature_measurement")))
        # set_temp = int(float(self.get_state("sensor.range_thermostat_heating_setpoint")))
        set_temp = int(float(self.get_state("sensor.range_oven_set_point")))

        # if set_temp == current_temp:
        self.alexa.announce(f"The oven has reached {set_temp} degrees.")
