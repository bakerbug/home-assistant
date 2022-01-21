import appdaemon.plugins.hass.hassapi as hass
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from google.oauth2 import service_account
import datetime
import requests
import yaml

SHEET_ID = "1uLGfHA8v5aa5MRoEaPOXU1SLFlr-lLsjzTtgfYyTv2U"
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SERVICE_ACCOUNT_FILE = 'google_keys.json'

######
# https://www.youtube.com/watch?v=cnPlKLEGR7E
######

class ChargeLogger(hass.Hass):
    def initialize(self):
        self.charge_connected = "binary_sensor.meco_charger_sensor"
        self.charge_level = "sensor.meco_battery_sensor"
        self.range = "sensor.meco_range_sensor"
        self.handle_active = self.listen_state(self.log_charge, entity_id=self.charge_level)

        self.log_charge('bogus', 'bogus', 'bogus', '80', 'bogus')

    def log_charge(self, entity, attribute, old, new, kwargs):
        charging = self.get_state(self.charge_connected) == "on"
        sheet_name = None
        credentials = None

        if not charging:
            return

        if new == "80":
            sheet_range = "'80% Charge'!A2:A"
            page_id = "349410544"
        elif new == "100":
            page_id = "440715400"
            sheet_range = "'100% Charge'!A2:A"
        else:
            return

        current_range = self.get_state(self.range)
        today = datetime.date.today().strftime('%x')

        credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        service = build('sheets', 'V4', credentials=credentials)
        sheet = service.spreasheets()
        result = sheet.values().get(spreadsheetId=SHEET_ID,
                                    range=sheet_range).execute()
        values = result.get('values', [])

        if not values:
            print("Try again...")
        else:
            for row in values:
                print(row[0], row[1])
