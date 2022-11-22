import appdaemon.plugins.hass.hassapi as hass

SLACK = "notify/slack_assistant"


class RotateTires(hass.Hass):
    def initialize(self):
        self.alexa = self.get_app("alexa_speak")
        self.mileage = "sensor.meco_odometer"
        self.rotate_goal = "input_number.meco_tire_rotation_due"
        self.rotate_button = "input_boolean.meco_rotate_tires"
        self.charger = "binary_sensor.tesla_wall_connector_vehicle_connected"

        self.monitor_handle = self.listen_state(self.mileage_monitor, self.charger)
        self.rotate_handle = self.listen_state(self.tires_rotated, self.rotate_button)

        self.turn_off(self.rotate_button)
        init_msg = "Initialized Rotate Tires."
        self.call_service(SLACK, message=init_msg)

    def mileage_monitor(self, entity, attribute, old, new, kwargs):
        if old == "off" and new == "on":
            mileage_string = self.get_state(self.mileage)
            self.call_service("notify/slack_assistant", message=mileage_string)
            current_mileage = float(self.get_state(self.mileage))
            goal_mileage = float(self.get_state(self.rotate_goal))

            countdown = goal_mileage - current_mileage

            if 0 < countdown < 100:
                msg = "Meeco is due for tire rotation. Please make an appointment for this service."
            elif countdown < 0:
                msg = "Meeco is past due for tire rotation.  Please schedule an appointment as soon as possible."
            else:
                return

            self.alexa.notify(msg)
            self.call_service(SLACK, message=msg)

        else:
            return

    def tires_rotated(self, entity, attribute, old, new, kwargs):
        self.turn_off(self.rotate_button)
        current_mileage = round(float(self.get_state(self.mileage)))
        self.set_value(self.rotate_goal, current_mileage + 15000)
