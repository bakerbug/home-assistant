import appdaemon.plugins.hass.hassapi as hass
import datetime
import json
import requests
import yaml


class VersionMonitor(hass.Hass):

    def initialize(self):
        self.ver_installed = self.get_state('sensor.installed_ha_version')
        self.ver_available = self.get_state('sensor.available_ha_version')
        self.update_time = datetime.time(18, 0, 0)
        self.has_been_announced = False
        with open('/home/homeassistant/.homeassistant/secrets.yaml', 'r') as secrets_file:
            config_data = yaml.load(secrets_file)
        self.alexa_notify_secret  = config_data['notify_me_key']

        self.ver_monitor = self.run_daily(self.report_new_version, self.update_time)

    def report_new_version(self, kwargs):
        if self.ver_installed == self.ver_available:
            self.has_been_announced = False
            return

        if self.has_been_announced:
            return

        alert_msg = 'A new version of Home Assistant is available. {} has been released.'.format(self.ver_available)
        body = json.dumps({'notification': alert_msg, 'accessCode': self.alexa_notify_secret})

        requests.post(url="https://api.notifymyecho.com/v1/NotifyMe", data=body)
        #self.call_service('notify/slack_assistant', message=alert_msg)
        self.has_been_announced = True
