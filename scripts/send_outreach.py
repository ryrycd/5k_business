#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import smtplib
import sys
import time
from datetime import timedelta
from email.message import EmailMessage
from email.utils import make_msgid
from pathlib import Path

from dotenv import load_dotenv

from lead_state import (
    LEAD_FIELDS,
    SEND_LOG_FIELDS,
    TERMINAL_STATUSES,
    REPLIED_STATUSES,
    ensure_csv,
    now_timestamp,
    parse_timestamp,
    read_csv_rows,
    to_int,
    write_csv_rows,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send or preview outreach emails from durable lead state.")
    parser.add_argument("--state", type=Path, default=Path("data/lead_state.csv"))
    parser.add_argument("--send-log", type=Path, default=Path("data/send_log.csv"))
    parser.add_argument("--queue-output", type=Path, default=Path("output/send-queue.csv"))
    parser.add_argument("--batch-size", type=int, default=int(os.getenv("OUTREACH_BATCH_SIZE", "20")))
    parser.add_argument("--min-score", type=int, default=int(os.getenv("OUTREACH_MIN_SCORE", "60")))
    parser.add_argument("--pause-seconds", type=float, default=float(os.getenv("OUTREACH_PAUSE_SECONDS", "1.0")))
    parser.add_argument("--live", action="store_true", help="Send live email via SMTP instead of only generating a queue")
    return parser.parse_args()


def smtp_config() -> dict[str, str]:
    return {
        "host": os.getenv("SMTP_HOST", "").strip(),
        "port": os.getenv("SMTP_PORT", "587").strip(),
        "username": os.getenv("SMTP_USERNAME", "").strip(),
        "password": os.getenv("SMTP_PASSWORD", "").strip(),
        "from_email": os.getenv("SMTP_FROM_EMAIL", os.getenv("SENDER_EMAIL", "")).strip(),
        "reply_to": os.getenv("REPLY_TO_EMAIL", os.getenv("SENDER_EMAIL", "")).strip(),
        "from_name": os.getenv("SENDER_NAME", "Lead Rescue AI").strip(),
        "use_tls": os.getenv("SMTP_USE_TLS", "true").strip().lower(),
    }


def subject_for_stage(row: dict[str, str], stage: str) -> str:
    subject = (row.get("subject_line") or f"Quick idea for {row.get('business_name', 'your team')}").strip()
    if stage == "initial":
        return subject
    if subject.lower().startswith("re:"):
        return subject
    return f"Re: {subject}"


def body_for_stage(row: dict[str, str], stage: str) -> str:
    if stage == "initial":
        body = row.get("email_body", "")
    elif stage == "follow_up_1":
        body = row.get("follow_up_1", "")
    else:
        body = row.get("follow_up_2", "")
    audit_url = (row.get("audit_page_url") or "").strip()
    if audit_url and audit_url not in body:
        body = f"{body}\n\nQuick audit page:\n{audit_url}".strip()
    return body


def next_stage(row: dict[str, str]) -> str | None:
    status = (row.get("status") or "").strip()
    send_count = to_int(row.get("send_count"))
    if status == "ready" and send_count == 0:
        return "initial"
    if status == "sent_1" and send_count == 1:
        return "follow_up_1"
    if status == "sent_2" and send_count == 2:
        return "follow_up_2"
    return None


def due_for_send(row: dict[str, str], min_score: int) -> bool:
    status = (row.get("status") or "").strip()
    if status in TERMINAL_STATUSES or status in REPLIED_STATUSES:
        return False
    if row.get("is_suppressed", "").lower() == "true" or row.get("opt_out", "").lower() == "true":
        return False
    if not (row.get("email") or "").strip():
        return False
    if to_int(row.get("opportunity_score")) < min_score:
        return False
    stage = next_stage(row)
    if not stage:
        return False
    next_contact = parse_timestamp(row.get("next_contact_at", ""))
    if next_contact is None:
        return True
    return next_contact <= parse_timestamp(now_timestamp())


def build_queue(rows: list[dict[str, str]], min_score: int, batch_size: int) -> list[dict[str, str]]:
    queue: list[dict[str, str]] = []
    sorted_rows = sorted(rows, key=lambda row: (-to_int(row.get("opportunity_score")), row.get("business_name", "")))
    for row in sorted_rows:
        if not due_for_send(row, min_score):
            continue
        stage = next_stage(row)
        if not stage:
            continue
        queue.append(
            {
                "lead_id": row.get("lead_id", ""),
                "business_name": row.get("business_name", ""),
                "email": row.get("email", ""),
                "opportunity_score": row.get("opportunity_score", ""),
                "stage": stage,
                "subject": subject_for_stage(row, stage),
                "body": body_for_stage(row, stage),
            }
        )
        if len(queue) >= batch_size:
            break
    return queue


def write_queue(path: Path, queue: list[dict[str, str]]) -> None:
    fieldnames = ["lead_id", "business_name", "email", "opportunity_score", "stage", "subject", "body"]
    write_csv_rows(path, queue, fieldnames)


def send_one(row: dict[str, str], config: dict[str, str], stage: str) -> tuple[str, str]:
    message = EmailMessage()
    message["From"] = f'{config["from_name"]} <{config["from_email"]}>'
    message["To"] = row["email"]
    message["Reply-To"] = config["reply_to"]
    message["Subject"] = subject_for_stage(row, stage)
    message_id = make_msgid(domain=config["from_email"].split("@", 1)[1] if "@" in config["from_email"] else None)
    message["Message-ID"] = message_id
    if row.get("thread_message_id"):
        message["In-Reply-To"] = row["thread_message_id"]
        message["References"] = row["thread_message_id"]
    message.set_content(body_for_stage(row, stage))

    with smtplib.SMTP(config["host"], int(config["port"]), timeout=30) as server:
        if config["use_tls"] not in {"false", "0", "no"}:
            server.starttls()
        if config["username"]:
            server.login(config["username"], config["password"])
        server.send_message(message)

    return message_id, "sent"


def apply_send_result(row: dict[str, str], stage: str, message_id: str) -> dict[str, str]:
    sent_at = now_timestamp()
    base_dt = parse_timestamp(sent_at)
    row["updated_at"] = sent_at
    row["last_contacted_at"] = sent_at
    row["last_outreach_stage"] = stage
    row["last_message_id"] = message_id
    if not row.get("thread_message_id"):
        row["thread_message_id"] = message_id
    send_count = to_int(row.get("send_count")) + 1
    row["send_count"] = str(send_count)

    follow_up_1_days = int(os.getenv("FOLLOW_UP_1_DELAY_DAYS", "2"))
    follow_up_2_days = int(os.getenv("FOLLOW_UP_2_DELAY_DAYS", "4"))
    if stage == "initial":
        row["status"] = "sent_1"
        if base_dt is not None:
            row["next_contact_at"] = (base_dt + timedelta(days=follow_up_1_days)).replace(microsecond=0).isoformat()
    elif stage == "follow_up_1":
        row["status"] = "sent_2"
        if base_dt is not None:
            row["next_contact_at"] = (base_dt + timedelta(days=follow_up_2_days)).replace(microsecond=0).isoformat()
    else:
        row["status"] = "sent_3"
        row["next_contact_at"] = ""
    return row


def main() -> int:
    load_dotenv()
    args = parse_args()

    ensure_csv(args.state, LEAD_FIELDS)
    ensure_csv(args.send_log, SEND_LOG_FIELDS)

    rows = read_csv_rows(args.state)
    queue = build_queue(rows, args.min_score, args.batch_size)
    write_queue(args.queue_output, queue)

    if not args.live:
        print(json.dumps({"mode": "dry_run", "queued": len(queue), "queue_output": str(args.queue_output)}))
        return 0

    config = smtp_config()
    required = ["host", "from_email", "reply_to"]
    if any(not config[key] for key in required):
        print(json.dumps({"mode": "live_skipped", "reason": "smtp_not_configured", "queued": len(queue)}))
        return 0

    send_log = read_csv_rows(args.send_log)
    leads_by_id = {row.get("lead_id", ""): row for row in rows}

    for item in queue:
        row = leads_by_id[item["lead_id"]]
        stage = item["stage"]
        try:
            message_id, result = send_one(row, config, stage)
            apply_send_result(row, stage, message_id)
            error = ""
        except smtplib.SMTPRecipientsRefused as exc:
            row["status"] = "bounced"
            row["bounce_count"] = str(to_int(row.get("bounce_count")) + 1)
            row["updated_at"] = now_timestamp()
            message_id = ""
            result = "bounced"
            error = str(exc)
        except Exception as exc:  # noqa: BLE001
            message_id = ""
            result = "error"
            error = str(exc)

        send_log.append(
            {
                "sent_at": now_timestamp(),
                "lead_id": item["lead_id"],
                "stage": stage,
                "to_email": item["email"],
                "subject": item["subject"],
                "message_id": message_id,
                "delivery_mode": "live",
                "result": result,
                "error": error,
            }
        )
        if args.pause_seconds:
            time.sleep(args.pause_seconds)

    write_csv_rows(args.state, list(leads_by_id.values()), LEAD_FIELDS)
    write_csv_rows(args.send_log, send_log, SEND_LOG_FIELDS)
    print(json.dumps({"mode": "live", "attempted": len(queue), "send_log": str(args.send_log)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
