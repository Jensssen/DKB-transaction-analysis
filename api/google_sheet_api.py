import os.path
from typing import List, Dict

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class GoogleSheetsApi:

    def __init__(self, scope: List[str] = ["https://www.googleapis.com/auth/spreadsheets"]):
        self.scope = scope
        self.credentials = self.authenticate()

    def authenticate(self) -> Credentials:
        creds = None
        if os.path.exists("token.json"):
            creds = Credentials.from_authorized_user_file("token.json", self.scope)
        if not creds or not creds.valid:
            try:
                creds.refresh(Request())
            except (RefreshError, AttributeError):
                try:
                    flow = InstalledAppFlow.from_client_secrets_file("credentials.json", self.scope)
                except FileNotFoundError:
                    raise "You have not activated your Google Sheet API (How to: https://developers.google.com/sheets/api/quickstart/go#enable_the_api)"
                creds = flow.run_local_server(port=0)
            with open("token.json", "w") as token:
                token.write(creds.to_json())
        return creds

    def create(self, title: str) -> str:
        """Creates a new Sheet the user has access to."""
        try:
            service = build("sheets", "v4", credentials=self.credentials)
            spreadsheet = {"properties": {"title": title}}
            spreadsheet = (
                service.spreadsheets()
                .create(body=spreadsheet, fields="spreadsheetId")
                .execute()
            )
            print(f"Spreadsheet ID: {(spreadsheet.get('spreadsheetId'))}")
            return spreadsheet.get("spreadsheetId")
        except HttpError as error:
            raise f"An error occurred: {error}"

    def add_new_sheet(self, spreadsheet_id: str, sheet_name: str):
        """
        Creates the batch_update the user has access to.
        Load pre-authorized user credentials from the environment.
        """
        try:
            service = build("sheets", "v4", credentials=self.credentials)
            body = {
                "requests": {
                    "addSheet": {
                        "properties": {
                            "title": sheet_name
                        }
                    }
                }
            }
            result = (
                service.spreadsheets()
                .batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body=body
                )
                .execute()
            )

            return result
        except HttpError as error:
            raise f"An error occurred: {error}"

    def rename_sheet(self, spreadsheet_id, sheet_name):
        """
        Creates the batch_update the user has access to.
        Load pre-authorized user credentials from the environment.
        """
        try:
            service = build("sheets", "v4", credentials=self.credentials)
            body = {
                "requests": {
                    "updateSheetProperties": {
                        "properties": {
                            "sheetId": 0,
                            "title": sheet_name
                        },
                        "fields": "title",

                    }
                }
            }
            service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=body).execute()

        except HttpError as error:
            raise f"An error occurred: {error}"

    def add_data(self, spreadsheet_id: str, range_name: str, value_input_option: str, data: List[List[str]]) -> Dict[
        str, str]:
        """
        Add data to existing spreadsheet.

        Args:
            spreadsheet_id: Unique ID of target spreadsheet.
            range_name: Range to update e.g. A1:B2
            value_input_option: Determines how input data should be interpreted. RAW for as-is upload or USER_ENTERED
                as if user typed the data into the UI.
            data: List of Lists with data that shall be added to gsheet.
        """
        try:
            service = build("sheets", "v4", credentials=self.credentials)
            values = data
            body = {"values": values}
            result = (
                service.spreadsheets()
                .values()
                .update(
                    spreadsheetId=spreadsheet_id,
                    range=range_name,
                    valueInputOption=value_input_option,
                    body=body,
                )
                .execute()
            )
            print(f"{result.get('updatedCells')} cells updated.")
            return result
        except HttpError as error:
            raise f"An error occurred: {error}"
