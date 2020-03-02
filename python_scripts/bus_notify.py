import appdaemon.plugins.hass.hassapi as hass
from datetime import date
import smtplib
import yaml
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


class BusNotify(hass.Hass):
    def initialize(self):
        self.debug_switch = "input_boolean.debug_bus_notify"
        self.NOTIFY = self.listen_state(self.send_notification, "input_boolean.bus_notify", new="on")
        self.alexa = self.get_app("alexa_speak")

        with open("/home/homeassistant/.homeassistant/secrets.yaml", "r") as secrets_file:
            config_data = yaml.safe_load(secrets_file)
        self.last_date = None
        self.debug_email = config_data["debug_email"]
        self.email_account = config_data["gmail_account"]
        self.email_username = config_data["gmail_username"]
        self.email_password = config_data["gmail_password"]
        self.email_recipients = config_data["bus_notify_list"]
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.smtp_tls = True

        init_msg = "Initialized Bus Notify."
        self.call_service("notify/slack_assistant", message=init_msg)

        if self.get_state(self.debug_switch) == "on":
            for name in self.email_recipients:
                debug_msg = "Recipient: {}".format(name)
                self.call_service("notify/slack_assistant", message=debug_msg)

    def send_notification(self, one, two, three, four, kwargs):
        current_date = date
        if self.last_date == current_date:
            self.alexa.respond("The bus notification has already been sent for today.")
            self.turn_off("input_boolean.bus_notify")
            return

        debug = self.get_state(self.debug_switch) == "on"
        if debug:
            dst_email = self.debug_email
            msg_text = "This is a debug email.\nThere are many like it, but this one is mine."
        else:
            dst_email = self.email_recipients
            msg_text = "Good morning!\n\nKyle Baker will be riding his bicycle home today.\n\nThanks!\n-Bill"

        self.last_date = current_date

        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Kyle Baker - No Bus Today"
        msg["From"] = self.email_account
        msg["To"] = ", ".join(dst_email)
        msg.attach(MIMEText(msg_text))
        session = smtplib.SMTP(self.smtp_server, self.smtp_port)
        session.set_debuglevel(1)
        session.starttls()
        session.login(self.email_username, self.email_password)
        session.sendmail(self.email_account, dst_email, msg.as_string())
        session.quit()

        self.turn_off("input_boolean.bus_notify")

        self.alexa.respond("I have notified the bus.")

    def slack_debug(self, message):
        debug = self.get_state(self.debug_switch) == "on"
        if debug:
            self.call_service("notify/slack_assistant", message=message)
