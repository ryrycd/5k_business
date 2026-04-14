#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

CHAT_HINTS = [
    "intercom",
    "drift",
    "tawk",
    "zendesk",
    "livechat",
    "chat widget",
    "chat with us",
    "start chat",
    "launcher",
    "olark",
]

BOOKING_HINTS = [
    "calendly",
    "book now",
    "schedule",
    "appointment",
    "book online",
    "reserve now",
]

SMS_HINTS = [
    "text us",
    "sms",
    "message us",
    "text now",
    "send us a text",
]

CTA_HINTS = [
    "call now",
    "call today",
    "book now",
    "schedule",
    "request estimate",
    "request quote",
    "free estimate",
    "free quote",
    "contact us",
    "get started",
]

EMERGENCY_HINTS = [
    "24/7",
    "emergency",
    "same day",
    "after hours",
    "rapid response",
]

HIGH_VALUE_NICHES = {"roofing", "plumbing", "hvac", "restoration", "med spa", "cosmetic dentistry"}


@dataclass
class Prospect:
    business_name: str
    website: str
    city: str
    state: str
    niche: str
    email: str
    phone: str
    notes: str


def normalize_url(url: str) -> str:
    candidate = (url or "").strip()
    if not candidate:
        return ""
    if not candidate.startswith(("http://", "https://")):
        candidate = f"https://{candidate}"
    return candidate


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "prospect"


def load_prospects(path: Path) -> list[Prospect]:
    prospects: list[Prospect] = []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            prospects.append(
                Prospect(
                    business_name=(row.get("business_name") or "").strip(),
                    website=normalize_url(row.get("website") or ""),
                    city=(row.get("city") or "").strip(),
                    state=(row.get("state") or "").strip(),
                    niche=(row.get("niche") or "").strip(),
                    email=(row.get("email") or "").strip(),
                    phone=(row.get("phone") or "").strip(),
                    notes=(row.get("notes") or "").strip(),
                )
            )
    return prospects


def fetch_homepage(url: str, timeout: int = 15) -> tuple[str, str]:
    response = requests.get(
        url,
        timeout=timeout,
        headers={"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9"},
    )
    response.raise_for_status()
    return response.text, response.url


def count_matches(text: str, options: list[str]) -> int:
    lower_text = text.lower()
    return sum(1 for item in options if item in lower_text)


def detect_phone_numbers(text: str) -> list[str]:
    matches = re.findall(r"(?:\+?1[-.\s]*)?(?:\(?\d{3}\)?[-.\s]*)\d{3}[-.\s]*\d{4}", text)
    unique = sorted(set(match.strip() for match in matches))
    return unique


def parse_site(html: str, resolved_url: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    page_text = soup.get_text(" ", strip=True)
    lower_html = html.lower()
    title = soup.title.get_text(strip=True) if soup.title else ""
    meta_description = ""
    meta_tag = soup.find("meta", attrs={"name": "description"})
    if meta_tag and meta_tag.get("content"):
        meta_description = str(meta_tag["content"]).strip()

    anchors = [element.get_text(" ", strip=True) for element in soup.select("a, button")]
    cta_count = sum(1 for item in anchors if any(hint in item.lower() for hint in CTA_HINTS))

    parsed_url = urlparse(resolved_url)
    domain = parsed_url.netloc
    forms = soup.find_all("form")

    has_chat = count_matches(lower_html, CHAT_HINTS) > 0
    has_booking = count_matches(lower_html, BOOKING_HINTS) > 0 or "calendly" in lower_html
    has_sms_cta = count_matches(page_text, SMS_HINTS) > 0
    emergency_service = count_matches(page_text, EMERGENCY_HINTS) > 0
    phones = detect_phone_numbers(page_text)

    return {
        "domain": domain,
        "resolved_url": resolved_url,
        "title": title,
        "meta_description": meta_description,
        "form_count": len(forms),
        "cta_count": cta_count,
        "has_chat": has_chat,
        "has_booking": has_booking,
        "has_sms_cta": has_sms_cta,
        "emergency_service": emergency_service,
        "phone_numbers_found": phones,
        "text_excerpt": page_text[:2000],
    }


def score_opportunity(prospect: Prospect, site: dict[str, Any]) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []
    niche = prospect.niche.lower()

    if niche in HIGH_VALUE_NICHES:
        score += 12
        reasons.append("high-ticket niche")

    if not site["has_chat"]:
        score += 24
        reasons.append("no visible chat widget")

    if not site["has_booking"]:
        score += 16
        reasons.append("no obvious booking flow")

    if not site["has_sms_cta"]:
        score += 10
        reasons.append("no text-first contact path")

    if site["form_count"] <= 1:
        score += 12
        reasons.append("lightweight lead capture")

    if site["cta_count"] <= 2:
        score += 14
        reasons.append("few strong calls to action")

    if site["emergency_service"]:
        score += 8
        reasons.append("speed matters for after-hours or urgent leads")

    if site["phone_numbers_found"]:
        score += 6
        reasons.append("phone-driven business likely depends on fast response")

    return min(score, 100), reasons


def band_for_score(score: int) -> str:
    if score >= 70:
        return "Hot"
    if score >= 45:
        return "Warm"
    return "Cool"


def rule_based_summary(prospect: Prospect, site: dict[str, Any], reasons: list[str]) -> dict[str, str]:
    hook = f"{prospect.business_name} already has the basics online, but there is room to tighten lead response."
    if not site["has_chat"]:
        hook = (
            f"{prospect.business_name} does not appear to have instant chat or after-hours lead capture on the site."
        )

    angle = "missed-call text-back and website lead qualification"
    if site["emergency_service"]:
        angle = "after-hours lead capture for urgent jobs and dispatch follow-up"

    first_line = (
        f"I took a quick look at {prospect.business_name}'s website and noticed there does not seem to be an "
        f"instant way for leads to get a response when the team is busy."
    )

    summary = (
        f"{hook} The biggest opening looks like {angle}, especially for a {prospect.niche or 'local service'} "
        f"business in {prospect.city}."
    )

    subject = f"Quick idea for {prospect.business_name}'s inbound leads"
    return {
        "personalization_line": first_line,
        "audit_summary": summary,
        "subject_line": subject,
        "recommended_angle": ", ".join(reasons[:3]) or angle,
    }


def ai_enrichment(client: Any, model: str, prospect: Prospect, site: dict[str, Any], score: int, reasons: list[str]) -> dict[str, str]:
    payload = {
        "business_name": prospect.business_name,
        "city": prospect.city,
        "state": prospect.state,
        "niche": prospect.niche,
        "website": prospect.website,
        "site_title": site["title"],
        "meta_description": site["meta_description"],
        "score": score,
        "reasons": reasons,
        "signals": {
            "has_chat": site["has_chat"],
            "has_booking": site["has_booking"],
            "has_sms_cta": site["has_sms_cta"],
            "form_count": site["form_count"],
            "cta_count": site["cta_count"],
            "emergency_service": site["emergency_service"],
        },
    }
    prompt = f"""
You are helping sell a local-service lead capture system.
Return strict JSON with these keys:
- personalization_line
- audit_summary
- subject_line
- recommended_angle

Rules:
- Keep each field concise.
- Do not mention AI hype.
- Focus on missed calls, slow web lead response, booking, and after-hours capture.
- Do not make claims that are not supported by the input.

Input:
{json.dumps(payload, indent=2)}
""".strip()

    response = client.responses.create(model=model, input=prompt)
    text = response.output_text.strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return rule_based_summary(prospect, site, reasons)
    required = {"personalization_line", "audit_summary", "subject_line", "recommended_angle"}
    if not required.issubset(parsed):
        return rule_based_summary(prospect, site, reasons)
    return {key: str(parsed[key]).strip() for key in required}


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


def write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
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

    parser = argparse.ArgumentParser(description="Audit prospect websites for missed-lead opportunity.")
    parser.add_argument("input_csv", type=Path, help="CSV of prospects")
    parser.add_argument("--output", type=Path, default=Path("output/audits.csv"), help="Output CSV path")
    parser.add_argument("--timeout", type=int, default=15, help="HTTP timeout in seconds")
    parser.add_argument("--pause", type=float, default=0.0, help="Pause between requests")
    parser.add_argument("--ai", action="store_true", help="Use OpenAI to enrich audit summaries")
    args = parser.parse_args()

    prospects = load_prospects(args.input_csv)
    if not prospects:
        print("No prospects found in input CSV.", file=sys.stderr)
        return 1

    client, model = build_openai_client(args.ai)
    rows: list[dict[str, Any]] = []

    for prospect in prospects:
        row: dict[str, Any] = {
            "business_name": prospect.business_name,
            "website": prospect.website,
            "city": prospect.city,
            "state": prospect.state,
            "niche": prospect.niche,
            "email": prospect.email,
            "phone": prospect.phone,
            "notes": prospect.notes,
        }

        try:
            html, resolved_url = fetch_homepage(prospect.website, timeout=args.timeout)
            site = parse_site(html, resolved_url)
            score, reasons = score_opportunity(prospect, site)
            enrichment = (
                ai_enrichment(client, model, prospect, site, score, reasons)
                if client is not None
                else rule_based_summary(prospect, site, reasons)
            )

            row.update(
                {
                    "resolved_url": site["resolved_url"],
                    "page_title": site["title"],
                    "meta_description": site["meta_description"],
                    "opportunity_score": score,
                    "opportunity_band": band_for_score(score),
                    "reason_flags": "; ".join(reasons),
                    "has_chat": site["has_chat"],
                    "has_booking": site["has_booking"],
                    "has_sms_cta": site["has_sms_cta"],
                    "emergency_service": site["emergency_service"],
                    "form_count": site["form_count"],
                    "cta_count": site["cta_count"],
                    "phone_numbers_found": "; ".join(site["phone_numbers_found"]),
                    **enrichment,
                }
            )
        except Exception as exc:  # noqa: BLE001
            row.update(
                {
                    "resolved_url": "",
                    "page_title": "",
                    "meta_description": "",
                    "opportunity_score": 0,
                    "opportunity_band": "Error",
                    "reason_flags": "",
                    "has_chat": "",
                    "has_booking": "",
                    "has_sms_cta": "",
                    "emergency_service": "",
                    "form_count": "",
                    "cta_count": "",
                    "phone_numbers_found": "",
                    "personalization_line": "",
                    "audit_summary": f"Could not audit site: {exc}",
                    "subject_line": "",
                    "recommended_angle": "",
                }
            )

        rows.append(row)
        if args.pause:
            time.sleep(args.pause)

    write_rows(args.output, rows)
    print(f"Wrote {len(rows)} audits to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
