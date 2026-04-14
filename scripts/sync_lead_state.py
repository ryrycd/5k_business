#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from dotenv import load_dotenv

from lead_state import (
    LEAD_FIELDS,
    SUPPRESSION_FIELDS,
    TERMINAL_STATUSES,
    REPLIED_STATUSES,
    ensure_csv,
    is_suppressed,
    lead_key,
    now_timestamp,
    normalize_email,
    read_csv_rows,
    sort_leads,
    suppression_sets,
    to_int,
    write_csv_rows,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync discovered prospects and generated outreach into durable lead state.")
    parser.add_argument("--prospects", type=Path, default=Path("output/fresh-prospects.csv"))
    parser.add_argument("--outreach", type=Path, default=Path("output/fresh-outreach.csv"))
    parser.add_argument("--state", type=Path, default=Path("data/lead_state.csv"))
    parser.add_argument("--suppression", type=Path, default=Path("data/suppression_list.csv"))
    return parser.parse_args()


def load_outreach_by_key(path: Path) -> dict[str, dict[str, str]]:
    rows = read_csv_rows(path)
    mapped: dict[str, dict[str, str]] = {}
    for row in rows:
        key = lead_key(row)
        if key:
            mapped[key] = row
    return mapped


def blank_lead() -> dict[str, str]:
    return {field: "" for field in LEAD_FIELDS}


def refresh_status(existing: dict[str, str], suppressed: bool) -> tuple[str, str]:
    status = (existing.get("status") or "").strip()
    send_count = to_int(existing.get("send_count"))
    if suppressed:
        return "opted_out", "suppressed"
    if status in TERMINAL_STATUSES or status in REPLIED_STATUSES:
        return status, existing.get("status_reason", "")
    if not normalize_email(existing.get("email", "")):
        return "needs_contact_path", "missing_email"
    if send_count == 0:
        return "ready", "fresh_email_target"
    return status or "ready", existing.get("status_reason", "")


def merge_lead(existing: dict[str, str], prospect: dict[str, str], outreach: dict[str, str], suppressed: bool) -> dict[str, str]:
    merged = blank_lead()
    merged.update(existing)
    merged["updated_at"] = now_timestamp()
    if not merged.get("created_at"):
        merged["created_at"] = merged["updated_at"]

    merged["lead_id"] = lead_key(prospect) or lead_key(existing)
    merged["source_query"] = prospect.get("source_query", merged.get("source_query", ""))
    merged["business_name"] = prospect.get("business_name", merged.get("business_name", ""))
    merged["niche"] = prospect.get("niche", merged.get("niche", ""))
    merged["city"] = prospect.get("city", merged.get("city", ""))
    merged["state"] = prospect.get("state", merged.get("state", ""))
    merged["website"] = prospect.get("website", merged.get("website", ""))
    merged["resolved_url"] = prospect.get("resolved_url", merged.get("resolved_url", ""))
    merged["domain"] = prospect.get("domain", merged.get("domain", "")) or merged["lead_id"]
    merged["email"] = normalize_email(prospect.get("email", merged.get("email", "")))
    merged["phone"] = prospect.get("phone", merged.get("phone", ""))
    merged["page_title"] = prospect.get("page_title", merged.get("page_title", ""))
    merged["meta_description"] = prospect.get("meta_description", merged.get("meta_description", ""))
    merged["opportunity_score"] = prospect.get("opportunity_score", merged.get("opportunity_score", ""))
    merged["opportunity_band"] = prospect.get("opportunity_band", merged.get("opportunity_band", ""))
    merged["reason_flags"] = prospect.get("reason_flags", merged.get("reason_flags", ""))
    merged["has_chat"] = prospect.get("has_chat", merged.get("has_chat", ""))
    merged["has_booking"] = prospect.get("has_booking", merged.get("has_booking", ""))
    merged["has_sms_cta"] = prospect.get("has_sms_cta", merged.get("has_sms_cta", ""))
    merged["emergency_service"] = prospect.get("emergency_service", merged.get("emergency_service", ""))
    merged["form_count"] = prospect.get("form_count", merged.get("form_count", ""))
    merged["cta_count"] = prospect.get("cta_count", merged.get("cta_count", ""))
    merged["personalization_line"] = prospect.get("personalization_line", merged.get("personalization_line", ""))
    merged["audit_summary"] = prospect.get("audit_summary", merged.get("audit_summary", ""))

    merged["subject_line"] = outreach.get("subject_line", merged.get("subject_line", ""))
    merged["email_body"] = outreach.get("email_body", merged.get("email_body", ""))
    merged["follow_up_1"] = outreach.get("follow_up_1", merged.get("follow_up_1", ""))
    merged["follow_up_2"] = outreach.get("follow_up_2", merged.get("follow_up_2", ""))
    merged["call_notes"] = outreach.get("call_notes", merged.get("call_notes", ""))

    merged["opt_out"] = "true" if suppressed or (merged.get("opt_out") or "").lower() == "true" else "false"
    merged["is_suppressed"] = "true" if suppressed else "false"
    status, reason = refresh_status(merged, suppressed)
    merged["status"] = status
    merged["status_reason"] = reason
    if status == "ready" and not merged.get("next_contact_at"):
        merged["next_contact_at"] = now_timestamp()
    return merged


def main() -> int:
    load_dotenv()
    args = parse_args()

    ensure_csv(args.state, LEAD_FIELDS)
    ensure_csv(args.suppression, SUPPRESSION_FIELDS)

    prospects = read_csv_rows(args.prospects)
    outreach_by_key = load_outreach_by_key(args.outreach)
    suppression_rows = read_csv_rows(args.suppression)
    email_suppressions, domain_suppressions = suppression_sets(suppression_rows)
    existing_rows = read_csv_rows(args.state)
    existing_by_key = {lead_key(row): row for row in existing_rows if lead_key(row)}

    for prospect in prospects:
        key = lead_key(prospect)
        if not key:
            continue
        existing = existing_by_key.get(key, blank_lead())
        merged = merge_lead(existing, prospect, outreach_by_key.get(key, {}), is_suppressed(prospect, email_suppressions, domain_suppressions))
        existing_by_key[key] = merged

    merged_rows = sort_leads(list(existing_by_key.values()))
    write_csv_rows(args.state, merged_rows, LEAD_FIELDS)

    summary = {
        "total_leads": len(merged_rows),
        "ready": sum(1 for row in merged_rows if row.get("status") == "ready"),
        "needs_contact_path": sum(1 for row in merged_rows if row.get("status") == "needs_contact_path"),
        "suppressed": sum(1 for row in merged_rows if row.get("is_suppressed") == "true"),
    }
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
