# Invoice parsing pipeline

Watches a Gmail label for invoice PDFs from approved senders, extracts the
data with Google Gemini (free tier), logs it to a Google Sheet, saves the
file to Drive, and posts a confirmation to Slack.

## How it works

1. `gmail_watcher.py` checks the `Invoices` Gmail label for new emails with
   PDF attachments, from senders on the whitelist only.
2. `pdf_extractor.py` pulls the raw text out of the PDF.
3. `ai_extractor.py` sends that text to Gemini and gets back structured
   fields (vendor, amount, dates, etc.) as JSON.
4. `sheets_writer.py` appends a row to the Google Sheet log.
5. `drive_uploader.py` saves the PDF into a Drive folder, organized by vendor.
6. `slack_notifier.py` posts a confirmation (or a failure alert) to Slack.
7. `main.py` ties all of the above together and repeats every
   `POLL_INTERVAL_SECONDS`.

## 1. One-time account setup (do this on your own machine, not in Docker)

### Google Cloud
1. Go to https://console.cloud.google.com/ and create a project (or reuse one).
2. Enable these APIs: Gmail API, Google Sheets API, Google Drive API.
3. Set up the OAuth consent screen (External, Testing mode is fine for a
   prototype) and add your own Google account as a test user.
4. Create OAuth 2.0 credentials (type: Desktop app) -> download as
   `credentials.json` -> place it in this folder.
5. Create a Service Account -> download its key -> save as
   `service_account.json` -> place it in this folder. This is used ONLY for
   Google Sheets (editing an existing sheet doesn't need storage quota).
6. Share your Google Sheet with the service account's email (found inside
   service_account.json, looks like `xxx@xxx.iam.gserviceaccount.com`) as
   an Editor. Drive does NOT need to be shared with the service account -
   Drive uploads use your own OAuth login instead, since service accounts
   have no storage quota of their own to create new files with.

### Gmail
1. Create a label called `Invoices` (or whatever you set in `.env`).
2. Set up a Gmail filter: "Has attachment" AND "From" contains your approved
   sender addresses -> apply the `Invoices` label automatically. This is
   your first layer of sender filtering.
3. Run this locally once (needs a browser) to complete the OAuth login for
   BOTH Gmail and Drive access. This creates `token.json`.
   ```
   python -c "from modules.google_auth import get_google_credentials; get_google_credentials()"
   ```
4. IMPORTANT: while the OAuth consent screen is in "Testing" mode, Google
   expires this login after 7 days. When you see a `RefreshError:
   invalid_grant` error in the logs, just delete `token.json` and re-run
   the command above to log in again. Moving this to production would mean
   getting the OAuth app verified by Google to avoid this.

### Slack
1. Create a Slack app at https://api.slack.com/apps ("Blank app"), add the
   `chat:write` scope, install it to your workspace, and copy the Bot Token
   (`xoxb-...`).
2. Invite the bot to your channel: `/invite @YourBotName`
3. Get the channel ID from the channel's details panel.

### Gemini (free tier)
1. Get a free API key at https://aistudio.google.com/apikey - no credit
   card required.
2. Note: the free tier is capped at a small number of requests per day
   (resets at midnight Pacific time). Each invoice processed uses one
   request. A paid key removes this cap for production use.

## 2. Configure environment variables

Copy `.env.example` to `.env` and fill in all the real values, including
`GMAIL_SENDER_WHITELIST` - a comma-separated list of approved sender email
addresses. This is the second layer of sender filtering (in code, as a
backstop to the Gmail filter above): even if an email somehow gets the
`Invoices` label from a sender not on this list, the code will skip it.

## 3. Build and run with Docker

```bash
docker build -t invoice-pipeline .
docker run -d \
  --name invoice-pipeline \
  --env-file .env \
  -v ${PWD}/token.json:/app/token.json \
  -v ${PWD}/credentials.json:/app/credentials.json \
  -v ${PWD}/service_account.json:/app/service_account.json \
  invoice-pipeline
```

## 4. Check it's working

```bash
docker logs -f invoice-pipeline
```

You should see "Invoice pipeline started" followed by a check every
`POLL_INTERVAL_SECONDS`. Send yourself a test email with a PDF attached,
from a whitelisted sender, to see it flow through.

To force an immediate check instead of waiting:
```bash
docker restart invoice-pipeline
```

## Sheet columns

The Google Sheet's first row should have these headers, in this order:
`Timestamp, Vendor, Billed To, Invoice Number, Amount, Currency,
Invoice Date, Due Date, Sender Email, Confidence, File Link`

## Notes

- `token.json`, `credentials.json`, `service_account.json`, and `.env` all
  contain secrets and are excluded via `.gitignore` - never commit them.
- If a row comes back with all fields blank and `confidence: low`, check
  the logs - `ai_extractor.py` prints Gemini's raw response when it can't
  be parsed as JSON, which usually reveals why (e.g. an invoice with
  multiple ambiguous reference numbers).
- This version only watches Gmail. Slack-as-a-source (people sharing
  invoices directly in Slack) can be added later as a second watcher module
  once needed.
