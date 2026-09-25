"""
Saves the invoice PDF into a Drive folder organized by vendor name.
Uses the shared OAuth login (your real Google account) rather than the
service account, since service accounts have no storage quota to create
new files with - only your own account does.
"""

import io
import os
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from modules.google_auth import get_google_credentials

ROOT_FOLDER_ID = os.environ["GOOGLE_DRIVE_ROOT_FOLDER_ID"]


def _get_drive_service():
    creds = get_google_credentials()
    return build("drive", "v3", credentials=creds)


def _get_or_create_vendor_folder(service, vendor_name):
    safe_name = vendor_name or "Unknown vendor"
    query = (
        f"name = '{safe_name}' and mimeType = 'application/vnd.google-apps.folder' "
        f"and '{ROOT_FOLDER_ID}' in parents and trashed = false"
    )
    results = service.files().list(q=query, fields="files(id, name)").execute()
    folders = results.get("files", [])
    if folders:
        return folders[0]["id"]

    folder_metadata = {
        "name": safe_name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [ROOT_FOLDER_ID],
    }
    folder = service.files().create(body=folder_metadata, fields="id").execute()
    return folder["id"]


def upload_pdf(pdf_bytes, filename, vendor_name):
    service = _get_drive_service()
    folder_id = _get_or_create_vendor_folder(service, vendor_name)

    media = MediaIoBaseUpload(io.BytesIO(pdf_bytes), mimetype="application/pdf")
    file_metadata = {"name": filename, "parents": [folder_id]}

    uploaded = (
        service.files()
        .create(body=file_metadata, media_body=media, fields="id, webViewLink")
        .execute()
    )
    return uploaded.get("webViewLink")
