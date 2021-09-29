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
        self.milage = "sensor.meco_mileage_sensor"
        self.range = "sensor.meco_range_sensor"
        self.handle_active = self.listen_state(self.log_charge, entity=self.charge_rate)
        self.log("Initializing ChargeLogger")

        # self.log_charge("bogus", "bogus", "31.8", "0.0", "bogus")

    def log_charge(self, entity, attribute, old, new, kwargs):
        charging = self.get_state(self.charge_connected) == "on"
        level = self.get_state(self.charge_level)
        rate = float(new)
        sheet_name = None
        credentials = None

        if not charging:
            return
        if rate > 0.0:
            return
        if old == new:
            return

        if level == "80":
            sheet_range = "'80% Charge'!A2"
        elif level == "100":
            sheet_range = "'100% Charge'!A2"
        else:
            sheet_range = "'Partial Charge'!A2"

        current_range = self.get_state(self.range)
        milage = self.get_state(self.milage)
        today = datetime.date.today().strftime("%x")
        level = f"{level}%"

        credentials = service_account.Credentials.from_service_account_file(self.SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        service = build("sheets", "v4", credentials=credentials)
        sheet = service.spreadsheets()
        self.log(f"Sheets: {sheet}")

        value_range_body = {"range": sheet_range, "majorDimension": "COLUMNS", "values": [[today], [current_range], [milage], [level]]}

        request = sheet.values().append(spreadsheetId=SHEET_ID, range=sheet_range, valueInputOption="USER_ENTERED", insertDataOption="INSERT_ROWS", body=value_range_body)
        response = request.execute()
