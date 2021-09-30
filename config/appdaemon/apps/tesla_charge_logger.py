import appdaemon.plugins.hass.hassapi as hass
from googleapiclient.discovery import build
from google.oauth2 import service_account
import datetime

SHEET_ID = "1uLGfHA8v5aa5MRoEaPOXU1SLFlr-lLsjzTtgfYyTv2U"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


class ChargeLogger(hass.Hass):
    def initialize(self):

        self.SERVICE_ACCOUNT_FILE = f"{self.config_dir}/google_keys.json"

        self.charge_connected = "binary_sensor.meco_charger_sensor"
        self.charge_level = "sensor.meco_battery_sensor"
        self.charge_rate = "sensor.meco_charging_rate_sensor"
        self.record_switch = "input_boolean.tesla_record_range"
        self.milage = "sensor.meco_mileage_sensor"
        self.range = "sensor.meco_range_sensor"
        self.auto_record = self.listen_state(self.auto_log, entity=self.charge_rate)
        self.manual_record = self.listen_state(self.manual_log, entity=self.record_switch, new="on")
        self.log("Initializing ChargeLogger")

    def auto_log(self, entity, attribute, old, new, kwargs):
        self.log(f"ChargeLogger.auto_log called.")
        rate = float(new)
        charging = self.get_state(self.charge_connected) == "on"

        if not charging:
            return
        if rate > 0.0:
            return
        if old == new:
            return

        self.log_charge()

    def manual_log(self, entity, attribute, old, new, kwargs):
        self.log(f"ChargeLogger.manual_log called.")
        self.turn_off(self.record_switch)

        self.log_charge()

    def log_charge(self):
        level = self.get_state(self.charge_level)
        sheet_name = None
        credentials = None

        if level == "80":
            sheet_range = "'80% Charge'!A2"
        elif level == "100":
            sheet_range = "'100% Charge'!A2"
        else:
            sheet_range = "'Partial Charge'!A2"

        current_range = self.get_state(self.range)
        mileage = self.get_state(self.milage)
        today = datetime.date.today().strftime("%x")
        level = f"{level}%"

        credentials = service_account.Credentials.from_service_account_file(self.SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        service = build("sheets", "v4", credentials=credentials)
        sheet = service.spreadsheets()
        self.log(f"Sheets: {sheet}")

        value_range_body = {"range": sheet_range, "majorDimension": "COLUMNS", "values": [[today], [current_range], [mileage], [level]]}

        request = sheet.values().append(spreadsheetId=SHEET_ID, range=sheet_range, valueInputOption="USER_ENTERED", insertDataOption="INSERT_ROWS", body=value_range_body)
        response = request.execute()
        self.log(f"Response: {response}")
