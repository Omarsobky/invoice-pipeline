"""Sends invoice text to Gemini (free tier) and asks for structured fields back as JSON."""

import json
import os
import google.generativeai as genai

genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-flash-latest")

EXTRACTION_PROMPT = """You will be given the raw text of an invoice PDF.
Extract the following fields and respond with ONLY a JSON object, no other text,
no markdown formatting, and no explanation - just the raw JSON object itself.

Some invoices have multiple reference numbers (Purchase Order, Order Number,
Customer Number, etc.) alongside the actual Invoice Number - use only the
value explicitly labeled as the invoice number, even if other numbers are
also present.

{{
  "vendor": "the company/person who sent/issued the invoice",
  "billed_to": "the person or company the invoice is addressed to (look for 'Bill to', 'Customer', etc.)",
  "invoice_number": "the value explicitly labeled as the invoice number, or null if not found",
  "amount": "the total/grand total amount due, as a number only, no currency symbol",
  "currency": "the currency code, e.g. USD, EGP, EUR, SAR",
  "invoice_date": "the invoice issue date in YYYY-MM-DD format, or null if not found",
  "due_date": "the payment due date in YYYY-MM-DD format, or null if not present on this invoice",
  "confidence": "high, medium, or low - your confidence in these extracted values"
}}

Invoice text:
---
{invoice_text}
---
"""


def extract_invoice_fields(invoice_text):
    response = model.generate_content(
        EXTRACTION_PROMPT.format(invoice_text=invoice_text)
    )

    raw_text = response.text.strip()
    # Strip markdown code fences if Gemini wraps the JSON in them
    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")
        raw_text = raw_text.replace("json\n", "", 1)

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        print(f"Could not parse Gemini's response as JSON. Raw response was:\n{raw_text}")
        return {
            "vendor": None,
            "billed_to": None,
            "invoice_number": None,
            "amount": None,
            "currency": None,
            "invoice_date": None,
            "due_date": None,
            "confidence": "low",
        }
