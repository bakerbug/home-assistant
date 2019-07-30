import appdaemon.plugins.hass.hassapi as hass
import datetime
import json
import requests
import yaml


class VersionMonitor(hass.Hass):

    def initialize(self):
        self.DEBUG = self.get_state('input_boolean.debug_version_monitor')
        self.update_time = datetime.time(0, 0, 0)
        with open('/home/homeassistant/.homeassistant/secrets.yaml', 'r') as secrets_file:
            config_data = yaml.load(secrets_file)
        self.alexa_notify_secret  = config_data['notify_me_key']
        self.notified_list = []

        self.ver_monitor = self.run_hourly(self.check_version, self.update_time)

        if self.DEBUG == 'on':
            debug_msg = 'Initializing Version Monitor.'
            self.call_service('notify/slack_assistant', message=debug_msg)

            # Initialization test
            self.report_new_version('0.0.0')

    def check_version(self, kwargs):
        self.DEBUG = self.get_state('input_boolean.debug_version_monitor')
        ver_available = self.get_state('sensor.available_ha_version')
        ver_installed = self.get_state('sensor.installed_ha_version')

        if self.DEBUG == 'on':
            debug_msg = 'Version monitor checking.  Installed: {} Available: {}'.format(ver_installed, ver_available)
            self.call_service('notify/slack_assistant', message=debug_msg)
            debug_msg = 'Notified List: {}'.format(self.notified_list)
            self.call_service('notify/slack_assistant', message=debug_msg)

        if ver_installed == ver_available:
            if self.notified_list:
                self.notified_list.clear()

                if self.DEBUG == 'on':
                    debug_msg = 'Installed version up to date. Purging notified list: {}'.format(self.notified_list)
                    self.call_service('notify/slack_assistant', message=debug_msg)

        elif ver_available not in self.notified_list:
            self.report_new_version(ver_available)

    def report_new_version(self, new_version):
        self.notified_list.append(new_version)
        alert_msg = 'A new version of Home Assistant is available. {} has been released.'.format(new_version)
        body = json.dumps({'notification': alert_msg, 'accessCode': self.alexa_notify_secret})

        if self.DEBUG == 'on':
            self.call_service('notify/slack_assistant', message=alert_msg)
            debug_msg = 'Notify List is now: {}'.format(self.notified_list)
            self.call_service('notify/slack_assistant', message=debug_msg)
        else:
            requests.post(url="https://api.notifymyecho.com/v1/NotifyMe", data=body)
