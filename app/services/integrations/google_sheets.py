# app/services/integrations/google_sheets.py
import json
from typing import Any

import gspread
from google.oauth2.service_account import Credentials

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


class GoogleSheetsService:
    _client: gspread.Client | None = None

    @classmethod
    def _get_client(cls) -> gspread.Client:
        if cls._client is None:
            creds_data = json.loads(settings.GOOGLE_CREDENTIALS_JSON or "{}")
            if not creds_data:
                raise ValueError("Google credentials not configured")
            credentials = Credentials.from_service_account_info(
                creds_data, scopes=SCOPES
            )
            cls._client = gspread.authorize(credentials)
        return cls._client

    @classmethod
    async def append_row(
        cls, spreadsheet_id: str, sheet_name: str, row: list[Any]
    ) -> None:
        import asyncio

        def _sync_append():
            client = cls._get_client()
            spreadsheet = client.open_by_key(spreadsheet_id)
            worksheet = spreadsheet.worksheet(sheet_name)
            worksheet.append_row(row, value_input_option="USER_ENTERED")

        await asyncio.get_event_loop().run_in_executor(None, _sync_append)
        logger.info(f"Row appended to {spreadsheet_id}/{sheet_name}")

    @classmethod
    async def read_sheet(
        cls, spreadsheet_id: str, sheet_name: str
    ) -> list[list[str]]:
        import asyncio

        def _sync_read():
            client = cls._get_client()
            spreadsheet = client.open_by_key(spreadsheet_id)
            worksheet = spreadsheet.worksheet(sheet_name)
            return worksheet.get_all_values()

        return await asyncio.get_event_loop().run_in_executor(None, _sync_read)