"""
Appends a row to the invoice tracking Google Sheet.

Setup required (one-time):
1. In Google Cloud Console, enable the "Google Sheets API" and "Google Drive API"
2. Create a Service Account -> download its JSON key -> save as service_account.json
   in this project's root folder
3. Open your Google Sheet and "Share" it with the service account's email address
   (found inside service_account.json, looks like xxx@xxx.iam.gserviceaccount.com)
   giving it Editor access
"""

import os
import gspread
from datetime import datetime

SHEET_ID = os.environ["GOOGLE_SHEET_ID"]


def append_row(invoice_data, sender, drive_file_link):
    gc = gspread.service_account(filename="service_account.json")
    sheet = gc.open_by_key(SHEET_ID).sheet1

    sheet.append_row(
        [
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            invoice_data.get("vendor"),
            invoice_data.get("billed_to"),
            invoice_data.get("invoice_number"),
            invoice_data.get("amount"),
            invoice_data.get("currency"),
            invoice_data.get("invoice_date"),
            invoice_data.get("due_date"),
            sender,
            invoice_data.get("confidence"),
            drive_file_link,
        ]
    )
