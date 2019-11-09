import appdaemon.plugins.hass.hassapi as hass
import yaml

class LocationMonitor(hass.Hass):

    def initialize(self):
        self.DEBUG = self.get_state('input_boolean.debug_location_monitor') == 'on'
        self.handle_bill = self.listen_state(self.location_change, entity='sensor.bill_location')
        self.handle_cricket = self.listen_state(self.location_change, entity='sensor.cricket_location')
        self.handle_front_door = self.listen_state(self.lock_change, entity='lock.front_door')
        self.alexa_list = ['media_player.kitchen', 'media_player.computer_room', 'media_player.master_bedroom']
        self.lock_list = ['lock.front_door',]
        self.SUN_ELEV_HIGH = 15.00

        self.code_data = None
        with open('/home/homeassistant/.homeassistant/secrets.yaml', 'r') as secrets_file:
            config_data = yaml.load(secrets_file)
            self.code_data = config_data["lock_code_data"]

        self.away_on_tuple = (
            'automation.hvac_balancing',
            'automation.lights_off_when_away',
            'automation.lights_on_when_away')

        self.away_off_tuple = (
            'automation.lights_on_at_early_sunset',
            'automation.lights_on_at_sunset',
            'automation.lights_on_for_weekday_mornings')

        self.home_on_tuple = (
            'automation.lights_on_at_early_sunset',
            'automation.lights_on_at_sunset',
            'automation.lights_on_for_weekday_mornings')

        self.home_off_tuple = (
            'automation.lights_off_when_away',
            'automation.lights_on_when_away')

        init_msg = 'Initialized Location Monitor.'
        self.slack(init_msg)

        if self.DEBUG:
            self.call_service('notify/alexa_media', message=init_msg, data={"type": "tts"},
                              target='media_player.computer_room')

        # For debugging
        #self.location_change('sensor.bill_location', 'bogus', 'Home', 'None', 'bogus')

    def location_change(self, entity, attribute, old, new, kwargs):
        self.DEBUG = self.get_state('input_boolean.debug_location_monitor') == 'on'
        self.NOTIFY = self.get_state('input_boolean.notify_location_monitor') == 'on'
        self.last_entity = entity
        self.last_old = old
        self.last_new = new

        if self.NOTIFY:
            self.generate_message()

        if new == 'Home' or old == 'Home':
            self.presence_behavior()

    def lock_change(self, entity, attribute, old, new, kwargs):
        lock_name = self.friendly_name(entity)
        lock_code = self.get_state(entity, attribute="code_id")
        if lock_code is not None:
            try:
                code_name = self.code_data[lock_code]
            except KeyError:
                code_name = f"Unregistered Code {lock_code}"

            lock_msg = f"{code_name} unlocked the {lock_name}."

        else:
            lock_msg = f"The {lock_name} has been {new}."

        self.alexa_notify(lock_msg)
        self.slack(lock_msg)

    def presence_behavior(self):
        bill_home = self.get_state('sensor.bill_location') == 'Home'
        cricket_home = self.get_state('sensor.cricket_location') == 'Home'
        sun_elevation = int(self.get_state('sun.sun', attribute='elevation'))
        time = self.get_state('sensor.time')
        hour, minute = time.split(':')
        hour = int(hour)
        light_msg = None
        lock_msg = None

        if bill_home or cricket_home:
            house_occupied = True
        else:
            house_occupied = False

        if self.last_new == 'Home':
            if sun_elevation < self.SUN_ELEV_HIGH:
                if 7 < hour < 22:
                    self.turn_on('group.evening_early_lights')
                    self.turn_on('group.evening_lights')
                    light_msg = '  Turning on all lights.'
                elif 7 >= hour or hour >= 22:
                    self.turn_on('group.evening_lights')
                    light_msg = 'Turning on some lights.'

            for automation in self.home_on_tuple:
                self.turn_on(automation)
            for automation in self.home_off_tuple:
                self.turn_off(automation)

        elif self.last_old == 'Home' and not house_occupied:
            for automation in self.away_on_tuple:
                self.turn_on(automation)
            for automation in self.away_off_tuple:
                self.turn_off(automation)

            self.turn_off('group.all_indoor_lights')
            light_msg = "Turning off all lights."

            for lock in self.lock_list:
                if self.get_state(lock) == 'unlocked':
                    name = self.friendly_name(lock)
                    self.call_service("lock/lock", entity_id = lock)
                    lock_msg = f'Locking {name}.'
                    self.slack(lock_msg)

        if light_msg is not None:
            self.slack(light_msg)

    def generate_message(self):
        if self.last_entity == 'sensor.bill_location':
            name = 'Bill'
        elif self.last_entity == 'sensor.cricket_location':
            name = 'Cricket'
        else:
            name = 'Unidentified Person'

        if self.last_old == 'None':
            direction = 'arrived at'
            location = self.last_new
        else:
            direction = 'departed from'
            location = self.last_old

        self.alexa_notify(f'{name} has {direction} {location}.')

    def alexa_notify(self, message):
        if self.DEBUG:
            target_list = 'media_player.computer_room'
        else:
            target_list = self.alexa_list

        self.call_service('notify/alexa_media', message=message, data={"type": "tts"},
                          target=target_list)

    def slack(self, message):
        notify = self.get_state('input_boolean.notify_location_monitor') == 'on'
        if notify:
            self.call_service("notify/slack_assistant", message=message)

    def slack_debug(self, message):
        debug = self.get_state("input_boolean.debug_location_monitor") == "on"
        if debug:
            self.call_service("notify/slack_assistant", message=message)
