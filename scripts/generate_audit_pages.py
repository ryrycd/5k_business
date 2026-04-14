#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import re
from pathlib import Path

from dotenv import load_dotenv

from lead_state import LEAD_FIELDS, read_csv_rows, write_csv_rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate per-lead audit pages from durable lead state.")
    parser.add_argument("--state", type=Path, default=Path("data/lead_state.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("site/generated-audits"))
    parser.add_argument("--public-base-url", default="")
    return parser.parse_args()


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "lead"


def render_page(row: dict[str, str]) -> str:
    business = html.escape(row.get("business_name", "Business"))
    niche = html.escape(row.get("niche", "service"))
    city = html.escape(row.get("city", "your market"))
    summary = html.escape(row.get("audit_summary", "There is room to improve lead response."))
    reasons = [item.strip() for item in (row.get("reason_flags") or "").split(";") if item.strip()]
    reason_items = "\n".join(f"<li>{html.escape(item)}</li>" for item in reasons[:5]) or "<li>Lead response looks improvable.</li>"
    score = html.escape(row.get("opportunity_score", ""))
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{business} | Lead Rescue AI Audit</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 0; color: #1f2a21; background: #f6efe6; }}
    main {{ max-width: 860px; margin: 0 auto; padding: 40px 20px 60px; }}
    .card {{ background: #fffaf5; border: 1px solid #eadfce; border-radius: 18px; padding: 24px; margin-bottom: 18px; }}
    h1, h2 {{ margin: 0 0 12px; }}
    .eyebrow {{ text-transform: uppercase; font-size: 12px; letter-spacing: .12em; color: #a64b19; }}
    .score {{ font-size: 42px; color: #a64b19; font-weight: 700; }}
    a.button {{ display: inline-block; padding: 12px 18px; background: #355444; color: white; text-decoration: none; border-radius: 999px; }}
  </style>
</head>
<body>
  <main>
    <div class="card">
      <p class="eyebrow">Lead Rescue AI audit</p>
      <h1>{business}</h1>
      <p>{city} {niche} opportunity snapshot</p>
      <div class="score">{score}</div>
      <p>Opportunity score based on visible lead-capture gaps.</p>
    </div>
    <div class="card">
      <h2>What we noticed</h2>
      <p>{summary}</p>
      <ul>{reason_items}</ul>
    </div>
    <div class="card">
      <h2>What we would install</h2>
      <ul>
        <li>Missed-call text-back</li>
        <li>Instant website lead capture</li>
        <li>Qualification and callback routing</li>
        <li>Owner alerting and weekly summaries</li>
      </ul>
      <a class="button" href="../demo.html">Open the live demo</a>
    </div>
  </main>
</body>
</html>
"""


def main() -> int:
    load_dotenv()
    args = parse_args()
    rows = read_csv_rows(args.state)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    public_base = (args.public_base_url.strip() or "https://ryrycd.github.io/5k_business").rstrip("/")

    for row in rows:
        lead_id = row.get("lead_id", "")
        if not lead_id:
            continue
        filename = f"{slugify(lead_id)}.html"
        target = args.output_dir / filename
        target.write_text(render_page(row), encoding="utf-8")
        row["audit_page_path"] = str(target)
        row["audit_page_url"] = f"{public_base}/generated-audits/{filename}" if public_base else ""

    write_csv_rows(args.state, rows, LEAD_FIELDS)
    print(f"Generated {len(rows)} audit pages in {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
