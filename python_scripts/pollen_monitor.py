import appdaemon.plugins.hass.hassapi as hass
import datetime
import json
import requests
import yaml


class PollenMonitor(hass.Hass):

    def initialize(self):
        self.pollen_warning_level = 8.00
        #self.alert_time = datetime.time(19, 30, 0)
        self.alert_time = datetime.time(0, 30, 0)  # Hack to fix issue getting timezone correct
        self.DEBUG = self.get_state('input_boolean.debug_pollen_monitor')
        self.MESSAGE = self.get_state('input_boolean.notify_pollen_monitor')
        self.pollen_alert_active = self.get_state('input_boolean.active_pollen_monitor')
        self.pollen_index = self.get_state('sensor.allergy_index_tomorrow')
        self.pollen_rating = self.get_state('sensor.allergy_index_tomorrow', attribute='rating')
        with open('/home/homeassistant/.homeassistant/secrets.yaml', 'r') as secrets_file:
            config_data = yaml.load(secrets_file)
        self.alexa_notify_secret  = config_data['notify_me_key']

        self.daily_report = self.run_daily(self.report_pollen, self.alert_time)

        if self.DEBUG:
            self.call_service('notify/slack_assistant', message='Initializing Pollen Report')
            time, interval, kwargs = self.info_timer(self.daily_report)
            debug_msg = 'Daily report: {} every {} seconds.'.format(time, interval)
            self.call_service('notify/slack_assistant', message=debug_msg)

            current_time = datetime.datetime.now()
            self.call_service('notify/slack_assistant', message='Initialized at {}'.format(current_time))

    def report_pollen(self, kwargs):
        self.DEBUG = self.get_state('input_boolean.debug_pollen_monitor')
        self.MESSAGE = self.get_state('input_boolean.notify_pollen_monitor')
        self.pollen_alert_active = self.get_state('input_boolean.active_pollen_monitor')

        if self.pollen_alert_active == 'off':
            return

        # Test the pollen level
        if float(self.pollen_index) >= self.pollen_warning_level or self.MESSAGE == 'on':
            alert_msg = self.generate_alert_message()
            body = json.dumps({'notification': alert_msg, 'accessCode': self.alexa_notify_secret})
            requests.post(url="https://api.notifymyecho.com/v1/NotifyMe", data=body)

        if self.DEBUG == 'on':
            self.debug_next_alert()

    def debug_next_alert(self):
        time, interval, kwargs = self.info_timer(self.daily_report)
        debug_msg = 'Next pollen_monitor on {} every {} seconds.'.format(time, interval)
        self.call_service('notify/slack_assistant', message=debug_msg)

    def generate_alert_message(self):
        pollen_state = self.get_state('sensor.allergy_index_tomorrow', attribute='all')
        allergens = []

        for key, value in pollen_state['attributes'].items():
            if key.startswith('allergen_name'):
                allergens.append(value)

        allergen_count = len(allergens)
        if allergen_count == 1:
            alert_msg = 'Pollen Alert.  There are {} levels of {}.'.format(self.pollen_rating, allergens[0])
        elif allergen_count == 2:
            alert_msg = 'Pollen Alert.  There are {} levels of {} and {}.'.format(self.pollen_rating,
                                                                                  allergens[0], allergens[1])
        elif allergen_count > 2:
            alert_msg = 'Pollen Alert.  There are {} levels of {}, {} and {}.'.format(self.pollen_rating,
                                                                                      allergens[0], allergens[1],
                                                                                      allergens[2])
        else:
            alert_msg = 'Pollen Alert. The pollen level is {}.'.format(self.pollen_rating)

        return alert_msg
