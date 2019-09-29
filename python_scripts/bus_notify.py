import appdaemon.plugins.hass.hassapi as hass
import smtplib
import yaml
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


class BusNotify(hass.Hass):

    def initialize(self):
        self.DEBUG = self.get_state('input_boolean.debug_bus_notify') == 'on'
        self.NOTIFY = self.listen_state(self.send_notification, 'input_boolean.bus_notify', new='on')

        with open('/home/homeassistant/.homeassistant/secrets.yaml', 'r') as secrets_file:
            config_data = yaml.load(secrets_file)
        self.email_account = config_data['gmail_account']
        self.email_username = config_data['gmail_username']
        self.email_password = config_data['gmail_password']
        self.email_recipients = config_data['bus_notify_list']
        self.smtp_server = 'smtp.gmail.com'
        self.smtp_port = 587
        self.smtp_tls = True

        init_msg = 'Initialized Bus Notify.'
        self.call_service('notify/slack_assistant', message=init_msg)

        if self.DEBUG:
            for name in self.email_recipients:
                debug_msg = 'Recipient: {}'.format(name)
                self.call_service('notify/slack_assistant', message=debug_msg)

    def send_notification(self, one, two, three, four, kwargs):
        self.DEBUG = self.get_state('input_boolean.debug_bus_notify') == 'on'

        if self.DEBUG:
            debug_msg = 'Sending bus notification.'
            self.call_service('notify/slack_assistant', message=debug_msg)

        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'Kyle Baker - No Bus Today'
        msg['From'] = self.email_account
        msg['To'] = ", ".join(self.email_recipients)
        msg_text = 'Good morning!\n\nKyle Baker will be riding his bicycle home today.\n\nThanks!\n-Bill'
        msg.attach(MIMEText(msg_text))
        session = smtplib.SMTP(self.smtp_server, self.smtp_port)
        session.set_debuglevel(1)
        session.starttls()
        session.login(self.email_username, self.email_password)
        session.sendmail(self.email_account, self.email_recipients, msg.as_string())
        session.quit()

        self.turn_off('input_boolean.bus_notify')

        if self.DEBUG:
            debug_msg = 'Bus notification sent.'
            self.call_service('notify/slack_assistant', message=debug_msg)