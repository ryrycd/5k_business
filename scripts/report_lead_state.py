#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from lead_state import read_csv_rows, to_int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a markdown summary of durable lead state.")
    parser.add_argument("--state", type=Path, default=Path("data/lead_state.csv"))
    parser.add_argument("--output", type=Path, default=Path("output/lead-state-summary.md"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows = read_csv_rows(args.state)
    status_counts = Counter(row.get("status", "unknown") for row in rows)
    ready_rows = [row for row in rows if row.get("status") == "ready"]
    form_ready_rows = [row for row in rows if row.get("status") == "form_ready"]
    positive_rows = [row for row in rows if row.get("status") == "replied_positive"]
    sent_rows = [row for row in rows if (row.get("status") or "").startswith("sent_")]

    lines = [
        "# Lead State Summary",
        "",
        f"- Total leads: {len(rows)}",
        f"- Ready to send: {len(ready_rows)}",
        f"- Ready to submit by contact form: {len(form_ready_rows)}",
        f"- Mid-sequence sent: {len(sent_rows)}",
        f"- Positive replies: {len(positive_rows)}",
        "",
        "## Status counts",
        "",
    ]
    for status, count in sorted(status_counts.items()):
        lines.append(f"- {status}: {count}")

    lines.extend(["", "## Top ready leads", ""])
    for row in sorted(ready_rows, key=lambda item: to_int(item.get("opportunity_score")), reverse=True)[:10]:
        lines.append(
            f"- {row.get('business_name', '')} ({row.get('city', '')}, {row.get('state', '')}) - "
            f"score {row.get('opportunity_score', '')} - {row.get('email', 'no email')}"
        )
    if not ready_rows:
        lines.append("- No ready leads")

    lines.extend(["", "## Top form-ready leads", ""])
    for row in sorted(form_ready_rows, key=lambda item: to_int(item.get("opportunity_score")), reverse=True)[:10]:
        lines.append(
            f"- {row.get('business_name', '')} ({row.get('city', '')}, {row.get('state', '')}) - "
            f"score {row.get('opportunity_score', '')} - {row.get('contact_form_url', 'no form')}"
        )
    if not form_ready_rows:
        lines.append("- No form-ready leads")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote lead state summary to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
