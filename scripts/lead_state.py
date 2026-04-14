#!/usr/bin/env python3
from __future__ import annotations

import csv
import re
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse


LEAD_FIELDS = [
    "lead_id",
    "created_at",
    "updated_at",
    "status",
    "status_reason",
    "source_query",
    "business_name",
    "niche",
    "city",
    "state",
    "website",
    "resolved_url",
    "domain",
    "email",
    "phone",
    "contact_page_url",
    "contact_form_url",
    "contact_form_method",
    "contact_form_fields_json",
    "outreach_channel",
    "page_title",
    "meta_description",
    "opportunity_score",
    "opportunity_band",
    "reason_flags",
    "has_chat",
    "has_booking",
    "has_sms_cta",
    "emergency_service",
    "form_count",
    "cta_count",
    "personalization_line",
    "audit_summary",
    "subject_line",
    "email_body",
    "follow_up_1",
    "follow_up_2",
    "call_notes",
    "send_count",
    "bounce_count",
    "last_contacted_at",
    "last_reply_at",
    "last_outreach_stage",
    "next_contact_at",
    "replied_category",
    "opt_out",
    "is_suppressed",
    "thread_message_id",
    "last_message_id",
    "form_submission_count",
    "last_form_submitted_at",
    "audit_page_path",
    "audit_page_url",
    "notes",
]

SUPPRESSION_FIELDS = ["created_at", "value", "type", "reason", "source", "notes"]
SEND_LOG_FIELDS = ["sent_at", "lead_id", "stage", "to_email", "subject", "message_id", "delivery_mode", "result", "error"]
REPLY_LOG_FIELDS = ["received_at", "lead_id", "from_email", "subject", "classification", "message_id", "uid", "excerpt"]
FORM_LOG_FIELDS = [
    "submitted_at",
    "lead_id",
    "form_url",
    "method",
    "result",
    "status_code",
    "error",
]
EMAIL_REGEX = re.compile(r"^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$", re.IGNORECASE)

TERMINAL_STATUSES = {"opted_out", "bounced", "closed_won", "closed_lost"}
REPLIED_STATUSES = {"replied_positive", "replied_negative", "replied_other"}


def now_timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def parse_timestamp(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv_rows(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        if rows:
            writer.writerows(rows)


def ensure_csv(path: Path, fieldnames: list[str]) -> None:
    if path.exists():
        return
    write_csv_rows(path, [], fieldnames)


def normalize_email(value: str) -> str:
    cleaned = (value or "").strip().lower()
    if not cleaned or not EMAIL_REGEX.match(cleaned):
        return ""
    if cleaned.endswith((".png", ".jpg", ".jpeg", ".svg", ".webp", ".gif")):
        return ""
    return cleaned


def root_domain(value: str) -> str:
    host = urlparse((value or "").strip()).netloc.lower().strip()
    return host.removeprefix("www.")


def lead_key(row: dict[str, str]) -> str:
    explicit = (row.get("lead_id") or row.get("domain") or "").strip().lower()
    if explicit:
        return explicit
    for key in ("resolved_url", "website"):
        domain = root_domain(row.get(key, ""))
        if domain:
            return domain
    email = normalize_email(row.get("email", ""))
    if "@" in email:
        return email.split("@", 1)[1]
    return ""


def to_int(value: str | int | None) -> int:
    try:
        return int(str(value or "0").strip())
    except ValueError:
        return 0


def suppression_sets(rows: list[dict[str, str]]) -> tuple[set[str], set[str]]:
    emails: set[str] = set()
    domains: set[str] = set()
    for row in rows:
        value = (row.get("value") or "").strip().lower()
        kind = (row.get("type") or "").strip().lower()
        if not value:
            continue
        if kind == "email":
            emails.add(value)
        elif kind == "domain":
            domains.add(value)
    return emails, domains


def is_suppressed(row: dict[str, str], email_suppressions: set[str], domain_suppressions: set[str]) -> bool:
    email = normalize_email(row.get("email", ""))
    domain = lead_key(row)
    return email in email_suppressions or domain in domain_suppressions


def add_suppression(
    rows: list[dict[str, str]],
    value: str,
    kind: str,
    reason: str,
    source: str,
    notes: str = "",
) -> list[dict[str, str]]:
    cleaned_value = (value or "").strip().lower()
    if not cleaned_value:
        return rows
    for row in rows:
        if (row.get("value") or "").strip().lower() == cleaned_value and (row.get("type") or "").strip().lower() == kind:
            return rows
    rows.append(
        {
            "created_at": now_timestamp(),
            "value": cleaned_value,
            "type": kind,
            "reason": reason,
            "source": source,
            "notes": notes,
        }
    )
    return rows


def sort_leads(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    def sort_key(row: dict[str, str]) -> tuple[int, int, str]:
        status = row.get("status", "")
        status_rank = 0 if status in {"ready", "form_ready"} else 1 if status.startswith(("sent_", "form_submitted_")) else 2
        return (
            status_rank,
            -to_int(row.get("opportunity_score")),
            row.get("business_name", ""),
        )

    return sorted(rows, key=sort_key)
