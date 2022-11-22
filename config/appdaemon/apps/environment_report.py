import appdaemon.plugins.hass.hassapi as hass

class EnvReport(hass.Hass):
    def initialize(self):
        self.alexa = self.get_app("alexa_speak")
        self.respond_switch = "input_boolean.environment_report"
        self.weather = "weather.khsv"
        self.turn_off(self.respond_switch)

        self.response_handler = self.listen_state(self.report, self.respond_switch, new="on")

    def report(self, entity, attribute, old, new, kwargs):
        self.turn_off(self.respond_switch)

        msg = ""

        garage_over_temp = int(self.get_state("sensor.garage_over_temp"))
        upstairs_humid = int(self.get_state("sensor.upstairs_thermostat_humidity"))
        downstairs_humid = int(self.get_state("sensor.downstairs_thermostat_humidity"))
        garage_humid = int(round(float(self.get_state("sensor.garage_humidity"))))
        outside_humid = int(self.get_state(self.weather, attribute="humidity"))

        if garage_over_temp > 0:
            msg = f"The garage over temperature is {garage_over_temp} degrees.  "

        msg = msg + f"The humidity is {upstairs_humid} percent upstairs, {downstairs_humid} percent downstairs, {garage_humid} percent in the garage, and {outside_humid} percent outside."
        self.alexa.respond(msg)


