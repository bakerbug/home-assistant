import appdaemon.plugins.hass.hassapi as hass
import datetime


class VersionMonitor(hass.Hass):
    def initialize(self):
        self.alexa = self.get_app("alexa_speak")
        self.debug_switch = "input_boolean.debug_version_monitor"
        self.tesla_update = "update.meco_software_update"
        self.update_time = datetime.time(0, 0, 0)
        self.notified_list = []

        self.ver_monitor = self.run_hourly(self.check_ha_version, self.update_time)
        self.tesla_monitor = self.listen_state(self.report_tesla_update, entity_id=self.tesla_update, new='on')

        init_msg = "Initialized Version Monitor."
        self.call_service("notify/slack_assistant", message=init_msg)

        debug = self.get_state(self.debug_switch) == "on"
        if debug:
            # Initialization test
            self.report_tesla_update("bogus", "2022.1.2.3", "bogus", "bogus", "bogus")

    def check_ha_version(self, kwargs):
        debug = self.get_state(self.debug_switch) == "on"
        ver_available = self.get_state("sensor.available_ha_version")
        ver_installed = self.get_state("sensor.installed_ha_version")

        if debug:
            debug_msg = "Version monitor checking.  Installed: {} Available: {}".format(ver_installed, ver_available)
            self.call_service("notify/slack_assistant", message=debug_msg)
            debug_msg = "Notified List: {}".format(self.notified_list)
            self.call_service("notify/slack_assistant", message=debug_msg)

        if ver_installed == ver_available:
            if self.notified_list:
                self.notified_list.clear()

                if debug:
                    debug_msg = "Installed version up to date. Purging notified list: {}".format(self.notified_list)
                    self.call_service("notify/slack_assistant", message=debug_msg)

        elif ver_available not in self.notified_list:
            self.report_ha_version(ver_available)

    def report_ha_version(self, new_version):
        self.notified_list.append(new_version)
        new_version = new_version.replace(".", " dot ")
        alert_msg = "A new version of Home Assistant is available. {} has been released.".format(new_version)
        self.alexa.notify(alert_msg)

    def report_tesla_update(self, entity, attribute, old, new, kwargs):
        new_version = self.get_state(self.tesla_update, attribute="latest_version")
        alert_msg = f"Tesla has released software update {new_version}."
        self.alexa.notify(alert_msg)
