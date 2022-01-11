import appdaemon.plugins.hass.hassapi as hass

class EnvReport(hass.Hass):
    def initialize(self):
        self.alexa = self.get_app("alexa_speak")
        self.respond_switch = "input_boolean.environment_report"
        self.temp_down = "sensor.downstairs_thermostat_temperature"
        self.temp_up = "sensor.upstairs_thermostat_temperature"
        self.weather = "weather.khsv"
        self.turn_off(self.respond_switch)

        self.response_handler = self.listen_state(self.report, self.respond_switch, new="on")

    def report(self, entity, attribute, old, new, kwargs):
        self.turn_off(self.respond_switch)
        upstairs_temp = int(self.get_state(self.temp_up))
        downstairs_temp = int(self.get_state(self.temp_down))
        outside_temp = int(self.get_state(self.weather, attribute="temperature"))
        upstairs_humid = int(self.get_state("sensor.upstairs_thermostat_humidity"))
        downstairs_humid = int(self.get_state("sensor.downstairs_thermostat_humidity"))
        outside_humid = int(self.get_state(self.weather, attribute="humidity"))

        msg = f"Upstairs it is {upstairs_temp} degrees with {upstairs_humid} percent humidity.  "
        msg = msg + f"Downstairs it is {downstairs_temp} degrees with {downstairs_humid} percent humidity.  "
        msg = msg + f"Outside it is {outside_temp} degrees with {outside_humid} percent humidity.  "

        self.alexa.respond(msg)


