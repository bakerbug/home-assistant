import appdaemon.plugins.hass.hassapi as hass
import datetime


class DebugApp(hass.Hass):
    def initialize(self):
        return
        self.alexa = self.get_app("alexa_speak")
        line1 = "Space Station will not be passing over soon."
        line2 = " The Shenzhou-11 Module will be passing over on Saturday, February 1 at 5:05 PM.  It will be appearing in the north-west and travel toward the east being visible for 540 seconds with a manitude of 2."
        line3 = " The Sl-4 R/B will be passing over on Sunday, February 2 at 5:54 AM.  It will be appearing in the south-east and travel toward the north being visible for 530 seconds with a manitude of 3.1."
        line4 = " The Atlas Centaur 2 R/B will be passing over on Saturday, February 1 at 5:36 PM.  It will be appearing in the west and travel toward the south-east being visible for 700 seconds with a manitude of 3.4."

        msg = line1 + line2 + line3 + line4
        self.alexa.respond(msg)
