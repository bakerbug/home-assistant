import appdaemon.plugins.hass.hassapi as hass
import datetime


class DebugApp(hass.Hass):
    def initialize(self):
        logger = self.get_main_log()
        timestamp = datetime.datetime.now()
        logger.log(50, f"Timmestamp is {timestamp}")
