#!/usr/bin/env python3
from __future__ import annotations

import argparse
import email
import imaplib
import json
import os
from email.header import decode_header
from email.policy import default
from email.utils import parseaddr
from pathlib import Path

from dotenv import load_dotenv

from lead_state import (
    LEAD_FIELDS,
    REPLIED_STATUSES,
    REPLY_LOG_FIELDS,
    SUPPRESSION_FIELDS,
    add_suppression,
    ensure_csv,
    lead_key,
    normalize_email,
    now_timestamp,
    read_csv_rows,
    write_csv_rows,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest and classify inbox replies via IMAP.")
    parser.add_argument("--state", type=Path, default=Path("data/lead_state.csv"))
    parser.add_argument("--suppression", type=Path, default=Path("data/suppression_list.csv"))
    parser.add_argument("--reply-log", type=Path, default=Path("data/reply_log.csv"))
    parser.add_argument("--inbox-state", type=Path, default=Path("data/inbox_state.json"))
    return parser.parse_args()


def decode_value(value: str | None) -> str:
    if not value:
        return ""
    parts = decode_header(value)
    decoded = []
    for text, encoding in parts:
        if isinstance(text, bytes):
            decoded.append(text.decode(encoding or "utf-8", errors="replace"))
        else:
            decoded.append(text)
    return "".join(decoded)


def extract_text(message: email.message.EmailMessage) -> str:
    if message.is_multipart():
        for part in message.walk():
            content_type = part.get_content_type()
            disposition = str(part.get("Content-Disposition") or "")
            if content_type == "text/plain" and "attachment" not in disposition.lower():
                try:
                    return part.get_content()
                except Exception:  # noqa: BLE001
                    continue
    try:
        return message.get_content()
    except Exception:  # noqa: BLE001
        return ""


def classify_reply(subject: str, body: str) -> str:
    text = f"{subject}\n{body}".lower()
    opt_out_terms = ["unsubscribe", "remove me", "do not contact", "stop emailing", "take me off", "stop"]
    positive_terms = ["interested", "sounds good", "let's talk", "lets talk", "call me", "send details", "demo", "pricing", "more info", "available"]
    negative_terms = ["not interested", "no thanks", "no thank you", "not now", "not a fit", "not relevant"]
    if any(term in text for term in opt_out_terms):
        return "opt_out"
    if any(term in text for term in positive_terms):
        return "positive"
    if any(term in text for term in negative_terms):
        return "negative"
    return "other"


def load_inbox_state(path: Path) -> dict[str, int]:
    if not path.exists():
        return {"last_uid": 0}
    return json.loads(path.read_text(encoding="utf-8"))


def save_inbox_state(path: Path, state: dict[str, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def find_lead(leads: list[dict[str, str]], sender_email: str) -> dict[str, str] | None:
    for lead in leads:
        if normalize_email(lead.get("email", "")) == sender_email:
            return lead
    sender_domain = sender_email.split("@", 1)[1] if "@" in sender_email else ""
    for lead in leads:
        if lead_key(lead) == sender_domain:
            return lead
    return None


def main() -> int:
    load_dotenv()
    args = parse_args()

    ensure_csv(args.state, LEAD_FIELDS)
    ensure_csv(args.suppression, SUPPRESSION_FIELDS)
    ensure_csv(args.reply_log, REPLY_LOG_FIELDS)

    host = os.getenv("IMAP_HOST", "").strip()
    username = os.getenv("IMAP_USERNAME", "").strip()
    password = os.getenv("IMAP_PASSWORD", "").strip()
    port = int(os.getenv("IMAP_PORT", "993"))
    folder = os.getenv("IMAP_FOLDER", "INBOX").strip()

    if not all([host, username, password]):
        print(json.dumps({"mode": "skipped", "reason": "imap_not_configured"}))
        return 0

    leads = read_csv_rows(args.state)
    suppression_rows = read_csv_rows(args.suppression)
    reply_log = read_csv_rows(args.reply_log)
    inbox_state = load_inbox_state(args.inbox_state)
    last_uid = int(inbox_state.get("last_uid", 0))

    mailbox = imaplib.IMAP4_SSL(host, port)
    mailbox.login(username, password)
    mailbox.select(folder)
    status, data = mailbox.uid("search", None, "ALL")
    if status != "OK":
        mailbox.logout()
        raise SystemExit(1)

    uids = [int(item) for item in (data[0] or b"").split() if int(item) > last_uid]
    processed = 0

    for uid in sorted(uids):
        status, msg_data = mailbox.uid("fetch", str(uid), "(RFC822)")
        if status != "OK" or not msg_data:
            continue
        raw_message = msg_data[0][1]
        message = email.message_from_bytes(raw_message, policy=default)
        sender_email = normalize_email(parseaddr(message.get("From"))[1])
        subject = decode_value(message.get("Subject"))
        body = extract_text(message).strip()
        excerpt = body[:500]
        classification = classify_reply(subject, body)
        lead = find_lead(leads, sender_email)
        lead_id = lead.get("lead_id", "") if lead else ""
        message_id = decode_value(message.get("Message-ID"))

        if lead is not None:
            lead["updated_at"] = now_timestamp()
            lead["last_reply_at"] = now_timestamp()
            lead["replied_category"] = classification
            if classification == "opt_out":
                lead["status"] = "opted_out"
                lead["opt_out"] = "true"
                lead["is_suppressed"] = "true"
                suppression_rows = add_suppression(suppression_rows, sender_email, "email", "opt_out_reply", "imap")
            elif classification == "positive":
                lead["status"] = "replied_positive"
            elif classification == "negative":
                lead["status"] = "replied_negative"
            else:
                if lead.get("status") not in REPLIED_STATUSES:
                    lead["status"] = "replied_other"

        reply_log.append(
            {
                "received_at": now_timestamp(),
                "lead_id": lead_id,
                "from_email": sender_email,
                "subject": subject,
                "classification": classification,
                "message_id": message_id,
                "uid": str(uid),
                "excerpt": excerpt,
            }
        )
        processed += 1
        last_uid = max(last_uid, uid)

    mailbox.logout()
    write_csv_rows(args.state, leads, LEAD_FIELDS)
    write_csv_rows(args.suppression, suppression_rows, SUPPRESSION_FIELDS)
    write_csv_rows(args.reply_log, reply_log, REPLY_LOG_FIELDS)
    save_inbox_state(args.inbox_state, {"last_uid": last_uid})
    print(json.dumps({"processed": processed, "last_uid": last_uid}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
