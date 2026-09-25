"""
Posts a confirmation message to Slack once an invoice is logged.

Setup required (one-time):
1. Go to https://api.slack.com/apps -> "Create New App" -> From scratch
2. Under "OAuth & Permissions", add the "chat:write" scope
3. Install the app to your workspace -> copy the "Bot User OAuth Token" (xoxb-...)
   into SLACK_BOT_TOKEN in your .env file
4. Invite the bot to your channel: in Slack, type `/invite @YourBotName` in the
   channel you want confirmations posted to
5. Get the channel ID (right-click the channel -> View channel details -> at
   the bottom) and put it in SLACK_CHANNEL_ID in your .env file
"""

import os
from slack_sdk import WebClient

client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])
CHANNEL_ID = os.environ["SLACK_CHANNEL_ID"]


def post_confirmation(invoice_data, drive_link):
    vendor = invoice_data.get("vendor") or "Unknown vendor"
    amount = invoice_data.get("amount")
    currency = invoice_data.get("currency") or ""
    confidence = invoice_data.get("confidence", "unknown")

    text = (
        f"*Invoice logged:* {vendor} - {amount} {currency}\n"
        f"Confidence: {confidence} | <{drive_link}|View file>"
    )

    client.chat_postMessage(channel=CHANNEL_ID, text=text)


def post_failure_alert(sender, filename, reason):
    text = (
        f":warning: *Could not process invoice*\n"
        f"From: {sender} | File: {filename}\nReason: {reason}"
    )
    client.chat_postMessage(channel=CHANNEL_ID, text=text)
