import appdaemon.plugins.hass.hassapi as hass

class LocationMonitor(hass.Hass):

    def initialize(self):
        self.handle_bill = self.listen_state(self.location_change, entity='sensor.bill_location')
        self.handle_cricket = self.listen_state(self.location_change, entity='sensor.cricket_location')

        init_msg = 'Initialized Location Monitor.'
        self.call_service('notify/slack_assistant', message=init_msg)


    def location_change(self, entity, attribute, old, new, kwargs):
        self.DEBUG = self.get_state('input_boolean.debug_location_monitor') == 'on'
        self.ACTIVE = self.get_state('input_boolean.notify_location_monitor') == 'on'

        if not self.ACTIVE:
            return
        if self.DEBUG:
            self.target_list = 'media_player.computer_room'
            debug_msg = f'Entity: {entity}, Attribute: {attribute}, Old: {old}, New: {new}'
            self.call_service('notify/slack_assistant', message=debug_msg)
        else:
            self.target_list = ['media_player.kitchen', 'media_player.computer_room', 'media_player.upstairs']

        if entity == 'sensor.bill_location':
            name = 'Bill'
        elif entity == 'sensor.cricket_location':
            name = 'Cricket'
        else:
            name = 'Unidentified Person'

        if old == 'None':
            direction = 'arrived at'
            location = new
        else:
            direction = 'departed from'
            location = old

        alexa_msg = f'{name} has {direction} {location}.'
        self.call_service('notify/alexa_media', message=alexa_msg, data={"type": "tts"},
                          target=self.target_list)




