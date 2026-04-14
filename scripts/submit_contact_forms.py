#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from datetime import timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv

from lead_state import FORM_LOG_FIELDS, LEAD_FIELDS, ensure_csv, now_timestamp, parse_timestamp, read_csv_rows, to_int, write_csv_rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Submit simple contact forms for leads without email but with detected forms.")
    parser.add_argument("--state", type=Path, default=Path("data/lead_state.csv"))
    parser.add_argument("--form-log", type=Path, default=Path("data/form_log.csv"))
    parser.add_argument("--queue-output", type=Path, default=Path("output/form-queue.csv"))
    parser.add_argument("--batch-size", type=int, default=int(os.getenv("FORM_BATCH_SIZE", "10")))
    parser.add_argument("--live", action="store_true", help="Submit live HTTP form requests")
    return parser.parse_args()


def sender_profile() -> dict[str, str]:
    return {
        "name": os.getenv("SENDER_NAME", "Lead Rescue AI"),
        "email": os.getenv("SENDER_EMAIL", "hello@example.com"),
        "company": os.getenv("SENDER_COMPANY", "Lead Rescue AI"),
        "phone": os.getenv("SENDER_PHONE", "555-555-5555"),
    }


def message_for_lead(row: dict[str, str]) -> str:
    audit = row.get("audit_summary", "I found a simple lead-response opportunity.")
    business = row.get("business_name", "your team")
    message = (
        f"I took a quick look at {business}'s website and noticed {audit} "
        "We install missed-call text-back, instant website lead capture, and simple qualification routing. "
        "If useful, I can send a short demo tailored to your workflow."
    )
    audit_url = (row.get("audit_page_url") or "").strip()
    if audit_url:
        message = f"{message} Quick audit page: {audit_url}"
    return message


def field_payload(fields_json: str, row: dict[str, str], sender: dict[str, str]) -> dict[str, str]:
    payload: dict[str, str] = {}
    try:
        fields = json.loads(fields_json or "[]")
    except json.JSONDecodeError:
        fields = []
    first_name = sender["name"].split(" ", 1)[0]
    last_name = sender["name"].split(" ", 1)[1] if " " in sender["name"] else "Team"
    message = message_for_lead(row)
    for field in fields:
        name = str(field.get("name") or "")
        field_type = str(field.get("type") or "text").lower()
        lower_name = name.lower()
        if field_type == "hidden":
            payload[name] = str(field.get("value") or "")
        elif "first" in lower_name and "name" in lower_name:
            payload[name] = first_name
        elif "last" in lower_name and "name" in lower_name:
            payload[name] = last_name
        elif "company" in lower_name:
            payload[name] = sender["company"]
        elif "phone" in lower_name:
            payload[name] = sender["phone"]
        elif "email" in lower_name:
            payload[name] = sender["email"]
        elif "subject" in lower_name:
            payload[name] = f"Lead response idea for {row.get('business_name', 'your team')}"
        elif "message" in lower_name or "comment" in lower_name or "details" in lower_name or "inquiry" in lower_name:
            payload[name] = message
        elif lower_name in {"name", "fullname", "full_name"}:
            payload[name] = sender["name"]
        else:
            payload[name] = str(field.get("value") or "")
    return payload


def due_for_form(row: dict[str, str]) -> bool:
    if row.get("status") not in {"form_ready", "form_submitted_1"}:
        return False
    next_contact = parse_timestamp(row.get("next_contact_at", ""))
    if next_contact is None:
        return True
    return next_contact <= parse_timestamp(now_timestamp())


def build_queue(rows: list[dict[str, str]], batch_size: int) -> list[dict[str, str]]:
    queue: list[dict[str, str]] = []
    for row in sorted(rows, key=lambda item: (-to_int(item.get("opportunity_score")), item.get("business_name", ""))):
        if not row.get("contact_form_url") or not due_for_form(row):
            continue
        stage = "initial_form" if to_int(row.get("form_submission_count")) == 0 else "follow_up_form"
        queue.append(
            {
                "lead_id": row.get("lead_id", ""),
                "business_name": row.get("business_name", ""),
                "contact_form_url": row.get("contact_form_url", ""),
                "contact_form_method": row.get("contact_form_method", ""),
                "stage": stage,
            }
        )
        if len(queue) >= batch_size:
            break
    return queue


def main() -> int:
    load_dotenv()
    args = parse_args()
    ensure_csv(args.form_log, FORM_LOG_FIELDS)
    rows = read_csv_rows(args.state)
    queue = build_queue(rows, args.batch_size)
    write_csv_rows(
        args.queue_output,
        queue,
        ["lead_id", "business_name", "contact_form_url", "contact_form_method", "stage"],
    )

    if not args.live:
        print(json.dumps({"mode": "dry_run", "queued": len(queue), "queue_output": str(args.queue_output)}))
        return 0

    sender = sender_profile()
    form_log = read_csv_rows(args.form_log)
    row_by_id = {row.get("lead_id", ""): row for row in rows}

    for item in queue:
        row = row_by_id[item["lead_id"]]
        payload = field_payload(row.get("contact_form_fields_json", ""), row, sender)
        method = (row.get("contact_form_method") or "post").lower()
        status_code = ""
        error = ""
        result = "error"
        try:
            if method == "get":
                response = requests.get(row["contact_form_url"], params=payload, timeout=20)
            else:
                response = requests.post(row["contact_form_url"], data=payload, timeout=20)
            status_code = str(response.status_code)
            result = "submitted" if response.ok else "error"
        except Exception as exc:  # noqa: BLE001
            error = str(exc)

        if result == "submitted":
            row["updated_at"] = now_timestamp()
            row["last_form_submitted_at"] = now_timestamp()
            row["form_submission_count"] = str(to_int(row.get("form_submission_count")) + 1)
            if row["status"] == "form_ready":
                row["status"] = "form_submitted_1"
                row["next_contact_at"] = ((parse_timestamp(now_timestamp()) or parse_timestamp(now_timestamp())) + timedelta(days=3)).replace(microsecond=0).isoformat()
            else:
                row["status"] = "form_submitted_2"
                row["next_contact_at"] = ""

        form_log.append(
            {
                "submitted_at": now_timestamp(),
                "lead_id": item["lead_id"],
                "form_url": row.get("contact_form_url", ""),
                "method": method,
                "result": result,
                "status_code": status_code,
                "error": error,
            }
        )

    write_csv_rows(args.state, list(row_by_id.values()), LEAD_FIELDS)
    write_csv_rows(args.form_log, form_log, FORM_LOG_FIELDS)
    print(json.dumps({"mode": "live" if args.live else "dry_run", "queued": len(queue), "form_log": str(args.form_log)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
