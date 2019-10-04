import appdaemon.plugins.hass.hassapi as hass

class LocationMonitor(hass.Hass):

    def initialize(self):
        self.DEBUG = self.get_state('input_boolean.debug_location_monitor') == 'on'
        self.handle_bill = self.listen_state(self.location_change, entity='sensor.bill_location')
        self.handle_cricket = self.listen_state(self.location_change, entity='sensor.cricket_location')
        self.alexa_list = ['media_player.kitchen', 'media_player.computer_room', 'media_player.master_bedroom']
        self.SUN_ELEV_HIGH = 15.00
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
        self.call_service('notify/slack_assistant', message=init_msg)

        if self.DEBUG:
            self.call_service('notify/alexa_media', message=init_msg, data={"type": "tts"},
                              target='media_player.computer_room')

        # For debugging
        #self.location_change('sensor.bill_location', 'bogus', 'None', 'Home', 'bogus')

    def location_change(self, entity, attribute, old, new, kwargs):
        self.DEBUG = self.get_state('input_boolean.debug_location_monitor') == 'on'
        self.NOTIFY = self.get_state('input_boolean.notify_location_monitor') == 'on'
        self.last_entity = entity
        self.last_old = old
        self.last_new = new

        if self.NOTIFY:
            self.notify()

        if new == 'Home' or old == 'Home':
            self.presence_behavior()


    def presence_behavior(self):
        bill_home = self.get_state('sensor.bill_location') == 'Home'
        cricket_home = self.get_state('sensor.cricket_location') == 'Home'
        sun_elevation = int(self.get_state('sun.sun', attribute='elevation'))
        time = self.get_state('sensor.time')
        hour, minute = time.split(':')
        hour = int(hour)
        light_msg = None

        if bill_home or cricket_home:
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

        else:
            for automation in self.away_on_tuple:
                self.call_service('automation/turn_on', entity=automation)
            for automation in self.away_off_tuple:
                self.call_service('automation/turn_off', entity=automation)

            self.call_serivce('switch/turn_off', entity='group.all_indoor_lights')
            light_msg = "Turning off all lights."

        if light_msg is not None:
            self.call_service('notify/slack_assistant', message=light_msg)

    def notify(self):
        if self.DEBUG:
            target_list = 'media_player.computer_room'
        else:
            target_list = self.alexa_list

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

        alexa_msg = f'{name} has {direction} {location}.'
        self.call_service('notify/alexa_media', message=alexa_msg, data={"type": "tts"},
                          target=target_list)
        self.call_service('notify/slack_assistant', message=alexa_msg)

