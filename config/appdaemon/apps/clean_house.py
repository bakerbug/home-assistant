import appdaemon.plugins.hass.hassapi as hass
import datetime

ACTIVE_SWITCH = "input_boolean.clean_house"
CLEAN_TIME = datetime.time(1, 0, 0)
DEBUG_SWITCH = "input_boolean.debug_clean_house"
PUCK = "vacuum.puck"
LIGHTS = ("light.dining_room_light", "light.sky_lights", "light.ceiling_lights")


class CleanHouse(hass.Hass):
    def initialize(self):
        self.handle_cleaning_task = None
        self.handle_vacuum = None
        self.alexa = self.get_app("alexa_speak")

        self.turn_off(ACTIVE_SWITCH)
        self.handle_active = self.listen_state(self.on_active_change, entity=ACTIVE_SWITCH)
        init_msg = "Initialized Clean House."
        self.call_service("notify/slack_assistant", message=init_msg)

    def on_active_change(self, entity, attribute, old, new, kwargs):
        if new == "on":
            self.handle_cleaning_task = self.run_once(self.begin_cleaning, CLEAN_TIME)
            self.alexa.respond("Puck will begin cleaning at 1AM.")
        else:
            self.cancel_timer(self.handle_cleaning_task)

    def on_vacuum_change(self, entity, attribute, old, new, kwargs):
        self.slack_debug(f"on_vacuum_change Old: {old} New: {new}")
        if new == "cleaning":
            self.lights_on()
        elif new == "docked":
            self.end_cleaning()

    def lights_on(self):
        for light in LIGHTS:
            self.turn_on(light)
            self.slack_debug(f"Turning on {light}.")

    def lights_off(self):
        for light in LIGHTS:
            self.turn_off(light)
            self.slack_debug(f"Turning off {light}.")

    def begin_cleaning(self, kwargs):
        self.slack_msg("Beginning cleaning.")
        self.handle_vacuum = self.listen_state(self.on_vacuum_change, entity=PUCK)
        self.call_service("vacuum/start", entity_id=PUCK)
        # Turn off ACTIVE_SWITCH

    def end_cleaning(self):
        self.lights_off()
        self.cancel_listen_state(self.handle_vacuum)
        self.turn_off(ACTIVE_SWITCH)
        self.slack_msg("Cleaning complete.")

    def slack_debug(self, message):
        debug = self.get_state(DEBUG_SWITCH) == "on"
        message = "(clean_house) " + message
        if debug:
            self.call_service("notify/slack_assistant", message=message)

    def slack_msg(self, message):
        self.call_service("notify/slack_assistant", message=message)
