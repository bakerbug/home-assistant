import datetime
import json
import requests
import yaml

#import inflect

import appdaemon.plugins.hass.hassapi as hass

class BirthdayMonitor(hass.Hass):

    def initialize(self):
        self.BDAY_LIST = self.get_state('group.birthday_list', attribute='entity_id')
        # self.alert_time = datetime.time(19, 30, 0)
        self.alert_time = datetime.time(0, 30, 0)  # Hack to fix issue getting timezone correct
        self.check_list_handler = self.run_daily(self.check_list, self.alert_time)

        with open('/home/homeassistant/.homeassistant/secrets.yaml', 'r') as secrets_file:
            config_data = yaml.load(secrets_file)
        self.alexa_notify_secret  = config_data['notify_me_key']

        init_msg = 'Initialized Birthday Monitor.'
        self.call_service('notify/slack_assistant', message=init_msg)
        self.check_list('bogus')


    def check_list(self, kwargs):
        self.BDAY_LIST = self.get_state('group.birthday_list', attribute='entity_id')

        for bday in self.BDAY_LIST:
            print(f"CHECKING: {bday}")
            days_until = self.get_state(bday)
            who = self.get_state(bday, attribute="friendly_name")
            years = str(self.get_state(bday, attribute='current_years'))

            if days_until == '7':
                message = f"It is one week until {who}."
            elif days_until == '0':
                inf = inflect.engine()
                message = f"Today is {who}'s {inf.ordinal(years)} birthday!"
                #message = f"Today is {who}."
            else:
                message = None

            if message is not None:
                body = json.dumps({'notification': message, 'accessCode': self.alexa_notify_secret})
                requests.post(url="https://api.notifymyecho.com/v1/NotifyMe", data=body)
