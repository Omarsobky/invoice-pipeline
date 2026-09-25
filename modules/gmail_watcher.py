"""
Watches Gmail for new emails labeled as invoices and pulls out PDF attachments.
Uses the shared OAuth login from google_auth.py (see that file for setup steps).

Security: only processes emails from senders on ALLOWED_SENDERS (set via the
GMAIL_SENDER_WHITELIST environment variable, comma-separated). Emails from
anyone else get the Invoices label removed and are skipped, so the pipeline
can't be tricked by a random sender manually labeling a fake invoice.
"""

import base64
import os
from googleapiclient.discovery import build
from modules.google_auth import get_google_credentials

ALLOWED_SENDERS = [
    email.strip().lower()
    for email in os.environ.get("GMAIL_SENDER_WHITELIST", "").split(",")
    if email.strip()
]


def get_gmail_service():
    creds = get_google_credentials()
    return build("gmail", "v1", credentials=creds)


def _is_sender_allowed(sender_header):
    if not ALLOWED_SENDERS:
        # No whitelist configured - allow everyone (useful for initial testing,
        # but GMAIL_SENDER_WHITELIST should be set before real/production use)
        return True
    sender_lower = sender_header.lower()
    return any(allowed in sender_lower for allowed in ALLOWED_SENDERS)


def get_new_invoice_emails(label_name):
    """
    Returns a list of dicts: {message_id, sender, pdf_filename, pdf_bytes}
    Only returns emails that have NOT been processed yet (checked via a
    "Processed" label we add after handling each one).
    """
    service = get_gmail_service()

    label_id = _get_label_id(service, label_name)
    processed_label_id = _get_or_create_label(service, "Processed")

    query = f"label:{label_name} -label:Processed has:attachment filename:pdf"
    results = service.users().messages().list(userId="me", q=query).execute()
    messages = results.get("messages", [])

    invoices = []
    for msg_meta in messages:
        msg = service.users().messages().get(userId="me", id=msg_meta["id"]).execute()
        sender = next(
            (h["value"] for h in msg["payload"]["headers"] if h["name"] == "From"),
            "unknown",
        )

        if not _is_sender_allowed(sender):
            print(f"Skipping email from non-whitelisted sender: {sender}")
            # Mark as processed so it's not retried every cycle, but do NOT
            # extract or return its attachment - this sender isn't trusted.
            service.users().messages().modify(
                userId="me",
                id=msg_meta["id"],
                body={"addLabelIds": [processed_label_id]},
            ).execute()
            continue

        for part in msg["payload"].get("parts", []):
            if part.get("filename", "").lower().endswith(".pdf"):
                attachment_id = part["body"]["attachmentId"]
                attachment = (
                    service.users()
                    .messages()
                    .attachments()
                    .get(userId="me", messageId=msg_meta["id"], id=attachment_id)
                    .execute()
                )
                pdf_bytes = base64.urlsafe_b64decode(attachment["data"])
                invoices.append(
                    {
                        "message_id": msg_meta["id"],
                        "sender": sender,
                        "pdf_filename": part["filename"],
                        "pdf_bytes": pdf_bytes,
                    }
                )

        # Mark as processed so we don't pick it up again next poll
        service.users().messages().modify(
            userId="me",
            id=msg_meta["id"],
            body={"addLabelIds": [processed_label_id]},
        ).execute()

    return invoices


def _get_label_id(service, label_name):
    labels = service.users().labels().list(userId="me").execute().get("labels", [])
    for label in labels:
        if label["name"].lower() == label_name.lower():
            return label["id"]
    raise ValueError(f"Label '{label_name}' not found - create it in Gmail first.")


def _get_or_create_label(service, label_name):
    labels = service.users().labels().list(userId="me").execute().get("labels", [])
    for label in labels:
        if label["name"].lower() == label_name.lower():
            return label["id"]
    created = (
        service.users()
        .labels()
        .create(userId="me", body={"name": label_name})
        .execute()
    )
    return created["id"]
