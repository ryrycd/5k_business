#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def build_openai_client(use_ai: bool) -> tuple[Any | None, str]:
    if not use_ai:
        return None, ""
    if OpenAI is None:
        print("OpenAI package not installed; continuing without AI enrichment.", file=sys.stderr)
        return None, ""
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        print("OPENAI_API_KEY is missing; continuing without AI enrichment.", file=sys.stderr)
        return None, ""
    model = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")
    return OpenAI(api_key=api_key), model


def sender_profile() -> dict[str, str]:
    return {
        "name": os.getenv("SENDER_NAME", "Your Name"),
        "email": os.getenv("SENDER_EMAIL", "you@yourdomain.com"),
        "company": os.getenv("SENDER_COMPANY", "Lead Rescue AI"),
        "phone": os.getenv("SENDER_PHONE", "555-555-5555"),
        "address": os.getenv("SENDER_ADDRESS", "123 Main St, City, State ZIP"),
    }


def render_rule_based_email(row: dict[str, str], sender: dict[str, str]) -> dict[str, str]:
    business_name = row.get("business_name", "your team")
    niche = row.get("niche", "service")
    city = row.get("city", "your market")
    line = row.get("personalization_line") or (
        f"I took a quick look at {business_name}'s site and noticed there is room to tighten lead response."
    )
    summary = row.get("audit_summary") or (
        f"I think there is a simple opportunity to capture more {niche.lower()} leads without changing your whole stack."
    )
    angle = row.get("recommended_angle") or "missed-call text-back and instant website follow-up"
    subject_line = row.get("subject_line") or f"Quick idea for {business_name}"

    body = f"""Hi {business_name} team,

{line}

{summary}

We install a lightweight system for {niche.lower()} companies that handles missed-call text-back, instant website lead capture, and simple qualification/booking without replacing your existing website.

For a market like {city}, recovering even one or two good leads can usually pay for the setup quickly.

If useful, I can send over a short demo built around {business_name}'s current workflow.

{sender["name"]}
{sender["company"]}
{sender["email"]}
{sender["phone"]}
{sender["address"]}

If you would rather not hear from me again, reply and I will close the loop.
""".strip()

    follow_up_1 = f"""Hi {business_name} team,

Circling back on this because the opportunity still looks like {angle}.

If you want, I can send a 2-minute demo showing how missed calls and web leads could be routed automatically.

{sender["name"]}
""".strip()

    follow_up_2 = f"""Hi {business_name} team,

Last note from me. If after-hours or missed leads are already covered, no worries.

If not, I can share a short example install for a {niche.lower()} business and you can decide from there.

{sender["name"]}
""".strip()

    call_notes = (
        f"Anchor the conversation around one recovered {niche.lower()} job. "
        f"Lead with speed-to-lead, after-hours coverage, and easy installation."
    )

    return {
        "subject_line": subject_line,
        "email_body": body,
        "follow_up_1": follow_up_1,
        "follow_up_2": follow_up_2,
        "call_notes": call_notes,
    }


def ai_enrichment(client: Any, model: str, row: dict[str, str], sender: dict[str, str]) -> dict[str, str]:
    prompt = f"""
You write cold outreach for a local-service lead capture offer.
Return strict JSON with these keys:
- subject_line
- email_body
- follow_up_1
- follow_up_2
- call_notes

Rules:
- Keep the tone direct and calm.
- No hype, fake urgency, or exaggerated claims.
- Use the audit details.
- The email should stay short.
- Include sender identity and mailing address in the main email body.

Audit row:
{json.dumps(row, indent=2)}

Sender:
{json.dumps(sender, indent=2)}
""".strip()

    response = client.responses.create(model=model, input=prompt)
    text = response.output_text.strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return render_rule_based_email(row, sender)
    required = {"subject_line", "email_body", "follow_up_1", "follow_up_2", "call_notes"}
    if not required.issubset(parsed):
        return render_rule_based_email(row, sender)
    return {key: str(parsed[key]).strip() for key in required}


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    load_dotenv()

    parser = argparse.ArgumentParser(description="Generate outreach copy from prospect audits.")
    parser.add_argument("input_csv", type=Path, help="Audit CSV file")
    parser.add_argument("--output", type=Path, default=Path("output/outreach.csv"), help="Output CSV path")
    parser.add_argument("--limit", type=int, default=0, help="Optional max number of rows to process")
    parser.add_argument("--ai", action="store_true", help="Use OpenAI for richer outreach")
    args = parser.parse_args()

    sender = sender_profile()
    rows = load_rows(args.input_csv)
    if args.limit > 0:
        rows = rows[: args.limit]
    if not rows:
        print("No audit rows found.", file=sys.stderr)
        return 1

    client, model = build_openai_client(args.ai)
    generated: list[dict[str, str]] = []

    for row in rows:
        rendered = ai_enrichment(client, model, row, sender) if client is not None else render_rule_based_email(row, sender)
        generated.append(
            {
                "lead_id": row.get("lead_id", row.get("domain", "")),
                "domain": row.get("domain", ""),
                "website": row.get("website", ""),
                "resolved_url": row.get("resolved_url", ""),
                "business_name": row.get("business_name", ""),
                "email": row.get("email", ""),
                "city": row.get("city", ""),
                "state": row.get("state", ""),
                "niche": row.get("niche", ""),
                "source_query": row.get("source_query", ""),
                "opportunity_score": row.get("opportunity_score", ""),
                "opportunity_band": row.get("opportunity_band", ""),
                **rendered,
            }
        )

    write_rows(args.output, generated)
    print(f"Wrote {len(generated)} outreach rows to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
