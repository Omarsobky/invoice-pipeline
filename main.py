import os
import time
import traceback
from dotenv import load_dotenv

load_dotenv()

from modules.gmail_watcher import get_new_invoice_emails
from modules.pdf_extractor import extract_text
from modules.ai_extractor import extract_invoice_fields
from modules.sheets_writer import append_row
from modules.drive_uploader import upload_pdf
from modules.slack_notifier import post_confirmation, post_failure_alert

GMAIL_LABEL = os.environ.get("GMAIL_LABEL", "Invoices")
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL_SECONDS", 300))


def process_invoice(invoice):
    sender = invoice["sender"]
    filename = invoice["pdf_filename"]
    pdf_bytes = invoice["pdf_bytes"]

    print(f"Processing invoice from {sender}: {filename}")

    invoice_text = extract_text(pdf_bytes)
    if not invoice_text.strip():
        post_failure_alert(sender, filename, "Could not extract any text from PDF")
        return

    invoice_data = extract_invoice_fields(invoice_text)

    drive_link = upload_pdf(pdf_bytes, filename, invoice_data.get("vendor"))

    append_row(invoice_data, sender, drive_link)

    post_confirmation(invoice_data, drive_link)

    print(f"Done: {invoice_data}")


def run_once():
    invoices = get_new_invoice_emails(GMAIL_LABEL)
    print(f"Found {len(invoices)} new invoice(s)")

    for invoice in invoices:
        try:
            process_invoice(invoice)
        except Exception as e:
            print(f"Error processing invoice: {e}")
            traceback.print_exc()
            post_failure_alert(
                invoice["sender"], invoice["pdf_filename"], str(e)
            )


if __name__ == "__main__":
    print("Invoice pipeline started. Checking every", POLL_INTERVAL, "seconds.")
    while True:
        run_once()
        time.sleep(POLL_INTERVAL)
