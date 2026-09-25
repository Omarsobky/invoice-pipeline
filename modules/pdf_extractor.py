"""Pulls raw text out of an invoice PDF so it can be sent to the AI for parsing."""

import io
import pdfplumber


def extract_text(pdf_bytes):
    text_chunks = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_chunks.append(page_text)
    return "\n".join(text_chunks)
