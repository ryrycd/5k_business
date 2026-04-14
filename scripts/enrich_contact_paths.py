#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from dotenv import load_dotenv

from discover_prospects import detect_contact_form, fetch_homepage
from lead_state import LEAD_FIELDS, read_csv_rows, root_domain, write_csv_rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill contact form metadata for existing lead state rows.")
    parser.add_argument("--state", type=Path, default=Path("data/lead_state.csv"))
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--timeout", type=int, default=10)
    return parser.parse_args()


def refresh_channel(row: dict[str, str]) -> None:
    if row.get("email"):
        row["outreach_channel"] = "email"
        return
    if row.get("contact_form_url"):
        row["outreach_channel"] = "contact_form"
        if row.get("status") == "needs_contact_path":
            row["status"] = "form_ready"
            row["status_reason"] = "contact_form_available"
        return
    row["outreach_channel"] = "none"


def main() -> int:
    load_dotenv()
    args = parse_args()
    rows = read_csv_rows(args.state)
    if args.limit > 0:
        target_rows = rows[: args.limit]
    else:
        target_rows = rows

    enriched = 0
    for row in target_rows:
        if row.get("contact_form_url") or not row.get("website"):
            refresh_channel(row)
            continue
        try:
            html, resolved_url = fetch_homepage(row["website"], timeout=args.timeout)
            detected = detect_contact_form(html, resolved_url, args.timeout)
        except Exception:  # noqa: BLE001
            refresh_channel(row)
            continue
        if detected.get("contact_form_url"):
            row["contact_page_url"] = detected.get("contact_page_url", "")
            row["contact_form_url"] = detected.get("contact_form_url", "")
            row["contact_form_method"] = detected.get("contact_form_method", "")
            row["contact_form_fields_json"] = detected.get("contact_form_fields_json", "")
            enriched += 1
        refresh_channel(row)

    write_csv_rows(args.state, rows, LEAD_FIELDS)
    print(json.dumps({"rows": len(rows), "contact_forms_found": enriched}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
