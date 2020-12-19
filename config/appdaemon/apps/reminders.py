import appdaemon.plugins.hass.hassapi as hass
import calendar
import datetime
import time


class Reminders(hass.Hass):
    def initialize(self):
        # (<week>, <day>, <hour> <message>)  Week of the month, 0 based.  Day of the week, Monday == 0.
        self.reminders = ((2, 3, 6, "Today is recycling day."),)  # Third thursday of the month at 6 AM
        self.alexa = self.get_app("alexa_speak")
        self.debug_switch = "input_boolean.debug_reminders"
        self.update_time = datetime.time(0, 0, 0)
        self.reminder_clock = self.run_hourly(self.check_reminders, self.update_time)

        init_msg = "Initialized Reminders."
        self.call_service("notify/slack_assistant", message=init_msg)

    def check_reminders(self, kwargs):
        self.DEBUG = self.get_state(self.debug_switch) == "on"

        for reminder in self.reminders:
            self.week = reminder[0]
            self.day = reminder[1]
            self.hour = reminder[2]
            self.message = reminder[3]

            if self.DEBUG:
                debug_msg = "Checking Week {}, Day {}, Hour {}, Message: {}".format(self.week, self.day, self.hour, self.message)
                self.call_service("notify/slack_assistant", message=debug_msg)

            self.check_schedule()

    def check_schedule(self):
        today = datetime.datetime.now()
        this_year = today.year
        this_month = today.month
        this_day = today.day
        # this_hour = time.localtime().tm_hour - 5  # Subtract 5 to hack appdaemon's weird clock
        this_hour = time.localtime().tm_hour
        cal = calendar.monthcalendar(this_year, this_month)

        if cal[0][self.day] == 0:
            event_day = cal[self.week + 1][self.day]
            debug_msg = "Event day +1 to {}".format(event_day)
        else:
            event_day = cal[self.week][self.day]
            debug_msg = "Event day unchanged at {}".format(event_day)

        if self.DEBUG:
            self.call_service("notify/slack_assistant", message=debug_msg)

        if this_day == event_day and this_hour == self.hour:
            self.notify()
        elif self.DEBUG:
            debug_msg = "this_day {} == event_day {} and this_hour {} == self.hour {}".format(this_day, event_day, this_hour, self.hour)
            self.call_service("notify/slack_assistant", message=debug_msg)

    def notify(self):
        self.call_service("notify/slack_assistant", message=self.message)

        self.alexa.notify(self.message, self.debug_switch)
