import appdaemon.plugins.hass.hassapi as hass


class HumidityMonitor(hass.Hass):
    def initialize(self):
        self.alexa = self.get_app("alexa_speak")
        self.upstairs_state = "climate.upstairs"
        self.upstairs_humidity = "sensor.upstairs_thermostat_humidity"
        self.downstairs_state = "climate.downstairs"
        self.downstairs_humidity = "sensor.downstairs_thermostat_humidity"
        self.trigger = "input_boolean.humidity_monitor"

        self.trigger_upstairs = self.listen_state(self.on_upstairs_change, self.upstairs_humidity)
        self.trigger_downstairs = self.listen_state(self.on_downstairs_change, self.downstairs_humidity)
        self.prev_upstairs = int(self.get_state(self.upstairs_humidity))
        self.prev_downstairs = int(self.get_state(self.downstairs_humidity))

        self.alert_level = 45

        self.slack_debug("Initialized Humidity Monitor.")

    def on_upstairs_change(self, entity_id, attribute, old, new, kwargs):
        level = int(new)

        if self.prev_upstairs > level and level < self.alert_level:
            self.on_humidity_drop(entity_id, level)

        self.prev_upstairs = level

    def on_downstairs_change(self, entity_id, attribute, old, new, kwargs):
        level = int(new)

        if self.prev_downstairs > level and level < self.alert_level:
            self.on_humidity_drop(entity_id, level)

        self.prev_downstairs = level

    def on_humidity_drop(self, entity_id, low_level):
        upstate = self.get_state(self.upstairs_state);
        downstate = self.get_state(self.downstairs_state)

        if upstate == 'off' or downstate == "off":
            return

        reading_name = self.get_state(entity_id, attribute="friendly_name")

        msg = f"The {reading_name} is {low_level} percent.  Please check that the humidifier is running.  "
        self.slack_debug(msg)
        self.alexa.announce(msg)

    def slack_debug(self, message):
        self.call_service("notify/slack_assistant", message=message)
