# Outbound System

## Purpose

This layer turns discovered prospects into durable lead records, a send queue, and reply-aware state.

## Files

- `scripts/sync_lead_state.py`
- `scripts/send_outreach.py`
- `scripts/ingest_replies.py`
- `scripts/report_lead_state.py`
- `scripts/lead_state.py`

## Durable state files

- `data/lead_state.csv`
- `data/suppression_list.csv`
- `data/send_log.csv`
- `data/reply_log.csv`
- `data/inbox_state.json`
- `output/send-queue.csv`
- `output/lead-state-summary.md`

## Flow

1. `discover_prospects.py` creates fresh prospect rows.
2. `generate_outreach.py` creates message copy for those rows.
3. `sync_lead_state.py` merges them into `data/lead_state.csv`.
4. `ingest_replies.py` updates lead state from inbox replies when IMAP is configured.
5. `send_outreach.py` builds the next send queue and optionally sends live email.
6. `report_lead_state.py` creates a readable operational summary.

## Modes

### Dry-run mode

`send_outreach.py` without `--live`:

- writes `output/send-queue.csv`
- does not send real email
- lets us inspect who would be contacted next

### Live mode

`send_outreach.py --live`:

- uses SMTP credentials from `.env` or GitHub secrets
- sends the next eligible batch
- updates lead status
- appends to `data/send_log.csv`

## Required SMTP env vars for live sending

- `SENDER_NAME`
- `SENDER_EMAIL`
- `SENDER_COMPANY`
- `SENDER_PHONE`
- `SENDER_ADDRESS`
- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `SMTP_FROM_EMAIL`
- `REPLY_TO_EMAIL`

## Optional sending controls

- `OUTREACH_BATCH_SIZE`
- `OUTREACH_MIN_SCORE`
- `OUTREACH_PAUSE_SECONDS`
- `FOLLOW_UP_1_DELAY_DAYS`
- `FOLLOW_UP_2_DELAY_DAYS`
- `SEND_LIVE_OUTREACH`

## Required IMAP env vars for reply ingestion

- `IMAP_HOST`
- `IMAP_PORT`
- `IMAP_USERNAME`
- `IMAP_PASSWORD`
- `IMAP_FOLDER`

## Important current limitation

This system now manages state and queueing, but it still depends on a real sender account and real inbox access to become fully autonomous.

Without SMTP:

- queue generation works
- live sending does not happen

Without IMAP:

- sending works
- reply classification remains inactive
