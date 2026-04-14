#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from audit_prospects import (
    Prospect,
    ai_enrichment,
    band_for_score,
    build_openai_client,
    fetch_homepage,
    parse_site,
    rule_based_summary,
    score_opportunity,
)


SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"
BLOCKED_DOMAINS = {
    "facebook.com",
    "instagram.com",
    "linkedin.com",
    "yelp.com",
    "angi.com",
    "angi.com",
    "angiads.com",
    "homeadvisor.com",
    "yellowpages.com",
    "manta.com",
    "mapquest.com",
    "bbb.org",
    "thumbtack.com",
    "nextdoor.com",
    "youtube.com",
    "x.com",
    "twitter.com",
    "tiktok.com",
    "reddit.com",
    "craigslist.org",
    "gaf.com",
    "supplyhouse.com",
}
BLOCKED_URL_PARTS = {
    "/location/",
    "/locations/",
    "/roofing-contractors/",
    "/find-a-pro/",
    "/contractor/",
    "/dealers/",
}
CONTACT_TEXT_HINTS = ["contact", "request quote", "free estimate", "book now", "schedule"]
EMAIL_PATTERN = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)
PHONE_PATTERN = re.compile(r"(?:\+?1[-.\s]*)?(?:\(?\d{3}\)?[-.\s]*)\d{3}[-.\s]*\d{4}")
DEFAULT_NICHES = ["Roofing", "Plumbing", "HVAC", "Water Damage Restoration"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Discover and score new local-service business prospects.")
    parser.add_argument("--markets", type=Path, default=Path("data/markets.csv"), help="CSV of markets")
    parser.add_argument("--index", type=Path, default=Path("data/prospect_index.csv"), help="Persistent prospect index")
    parser.add_argument(
        "--fresh-output",
        type=Path,
        default=Path("output/fresh-prospects.csv"),
        help="CSV of newly discovered prospects in this run",
    )
    parser.add_argument(
        "--all-output",
        type=Path,
        default=Path("output/discovered-prospects.csv"),
        help="CSV export of all known prospects",
    )
    parser.add_argument(
        "--summary-output",
        type=Path,
        default=Path("output/discovery-summary.md"),
        help="Markdown summary for the latest run",
    )
    parser.add_argument("--niches", nargs="*", default=DEFAULT_NICHES, help="Niches to search")
    parser.add_argument("--markets-per-run", type=int, default=4, help="How many cities to process per run")
    parser.add_argument("--queries-per-market", type=int, default=1, help="How many queries to use per market/niche")
    parser.add_argument("--results-per-query", type=int, default=8, help="Search results to request per query")
    parser.add_argument("--timeout", type=int, default=10, help="HTTP timeout")
    parser.add_argument("--ai", action="store_true", help="Use OpenAI to enrich summaries")
    parser.add_argument("--dry-run", action="store_true", help="Print planned queries without calling external APIs")
    return parser.parse_args()


def load_markets(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def load_existing_index(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def save_rows(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        if not rows:
            return
        fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        if rows:
            writer.writerows(rows)


def root_domain(url: str) -> str:
    hostname = urlparse(url).netloc.lower().strip()
    hostname = hostname.removeprefix("www.")
    return hostname


def blocked_domain(url: str) -> bool:
    hostname = root_domain(url)
    lower_url = url.lower()
    return any(hostname == blocked or hostname.endswith(f".{blocked}") for blocked in BLOCKED_DOMAINS) or any(
        part in lower_url for part in BLOCKED_URL_PARTS
    )


def market_slice(markets: list[dict[str, str]], count: int) -> list[dict[str, str]]:
    if not markets:
        return []
    count = max(1, min(count, len(markets)))
    day_seed = datetime.now(UTC).timetuple().tm_yday - 1
    start = (day_seed * count) % len(markets)
    selection: list[dict[str, str]] = []
    for offset in range(count):
        selection.append(markets[(start + offset) % len(markets)])
    return selection


def build_queries(niche: str, city: str, state: str, queries_per_market: int) -> list[str]:
    templates = [
        "{niche} {city} {state}",
        "{city} {state} {niche} contractor",
        "{niche} company {city} {state}",
    ]
    rendered = [template.format(niche=niche, city=city, state=state) for template in templates]
    return rendered[: max(1, min(queries_per_market, len(rendered)))]


def brave_web_search(query: str, api_key: str, limit: int, timeout: int) -> list[dict[str, Any]]:
    response = requests.get(
        SEARCH_URL,
        params={"q": query, "count": limit, "search_lang": "en", "country": "us", "safesearch": "moderate"},
        headers={"Accept": "application/json", "X-Subscription-Token": api_key},
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    return payload.get("web", {}).get("results", [])


def extract_business_name(site: dict[str, Any], fallback_title: str) -> str:
    for candidate in [site.get("title", ""), fallback_title]:
        if not candidate:
            continue
        cleaned = re.split(r"\s[\-|:]\s", candidate, maxsplit=1)[0].strip()
        if cleaned:
            return cleaned
    return ""


def likely_contact_links(html: str, resolved_url: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    links: list[str] = []
    for anchor in soup.find_all("a", href=True):
        text = anchor.get_text(" ", strip=True).lower()
        href = str(anchor["href"]).strip()
        if not href or href.startswith("#"):
            continue
        if any(hint in text for hint in CONTACT_TEXT_HINTS) or any(hint in href.lower() for hint in ["contact", "quote", "estimate"]):
            links.append(urljoin(resolved_url, href))
    deduped: list[str] = []
    seen: set[str] = set()
    for link in links:
        if link not in seen:
            seen.add(link)
            deduped.append(link)
    return deduped[:2]


def extract_contact_details(text: str) -> tuple[list[str], list[str]]:
    emails = sorted(set(EMAIL_PATTERN.findall(text)))
    phones = sorted(set(match.strip() for match in PHONE_PATTERN.findall(text)))
    return emails, phones


def collect_contact_details(html: str, resolved_url: str, timeout: int) -> tuple[list[str], list[str]]:
    emails, phones = extract_contact_details(html)
    for link in likely_contact_links(html, resolved_url):
        try:
            follow_html, _ = fetch_homepage(link, timeout=timeout)
        except Exception:  # noqa: BLE001
            continue
        more_emails, more_phones = extract_contact_details(follow_html)
        emails = sorted(set(emails + more_emails))
        phones = sorted(set(phones + more_phones))
    return emails, phones


def empty_index_row() -> dict[str, str]:
    return {
        "discovered_at": "",
        "source_query": "",
        "business_name": "",
        "website": "",
        "resolved_url": "",
        "domain": "",
        "city": "",
        "state": "",
        "niche": "",
        "email": "",
        "phone": "",
        "page_title": "",
        "meta_description": "",
        "opportunity_score": "",
        "opportunity_band": "",
        "reason_flags": "",
        "has_chat": "",
        "has_booking": "",
        "has_sms_cta": "",
        "emergency_service": "",
        "form_count": "",
        "cta_count": "",
        "personalization_line": "",
        "audit_summary": "",
        "subject_line": "",
        "recommended_angle": "",
        "status": "new",
        "notes": "",
    }


def build_row(
    result: dict[str, Any],
    query: str,
    niche: str,
    city: str,
    state: str,
    timeout: int,
    client: Any | None,
    model: str,
) -> dict[str, str] | None:
    url = (result.get("url") or "").strip()
    if not url or blocked_domain(url):
        return None

    html, resolved_url = fetch_homepage(url, timeout=timeout)
    site = parse_site(html, resolved_url)
    business_name = extract_business_name(site, str(result.get("title") or ""))
    if not business_name:
        return None

    emails, phones = collect_contact_details(html, resolved_url, timeout)
    prospect = Prospect(
        business_name=business_name,
        website=url,
        city=city,
        state=state,
        niche=niche,
        email=emails[0] if emails else "",
        phone=phones[0] if phones else "",
        notes="",
    )
    score, reasons = score_opportunity(prospect, site)
    enrichment = (
        ai_enrichment(client, model, prospect, site, score, reasons)
        if client is not None
        else rule_based_summary(prospect, site, reasons)
    )

    row = empty_index_row()
    row.update(
        {
            "discovered_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
            "source_query": query,
            "business_name": business_name,
            "website": url,
            "resolved_url": site["resolved_url"],
            "domain": root_domain(site["resolved_url"]),
            "city": city,
            "state": state,
            "niche": niche,
            "email": prospect.email,
            "phone": prospect.phone,
            "page_title": site["title"],
            "meta_description": site["meta_description"],
            "opportunity_score": str(score),
            "opportunity_band": band_for_score(score),
            "reason_flags": "; ".join(reasons),
            "has_chat": str(site["has_chat"]),
            "has_booking": str(site["has_booking"]),
            "has_sms_cta": str(site["has_sms_cta"]),
            "emergency_service": str(site["emergency_service"]),
            "form_count": str(site["form_count"]),
            "cta_count": str(site["cta_count"]),
            **{key: value for key, value in enrichment.items()},
        }
    )
    return row


def merge_index(existing: list[dict[str, str]], fresh: list[dict[str, str]]) -> list[dict[str, str]]:
    merged: dict[str, dict[str, str]] = {}
    for row in existing:
        domain = row.get("domain") or root_domain(row.get("resolved_url", "") or row.get("website", ""))
        if not domain:
            continue
        merged[domain] = row

    for row in fresh:
        merged[row["domain"]] = row

    rows = list(merged.values())
    rows.sort(key=lambda item: (int(item.get("opportunity_score") or 0), item.get("business_name", "")), reverse=True)
    return rows


def summary_markdown(
    selected_markets: list[dict[str, str]],
    niches: list[str],
    fresh: list[dict[str, str]],
    all_rows: list[dict[str, str]],
) -> str:
    fresh_counter = Counter(row["niche"] for row in fresh)
    hot = sum(1 for row in fresh if int(row.get("opportunity_score") or 0) >= 70)
    warm = sum(1 for row in fresh if 45 <= int(row.get("opportunity_score") or 0) < 70)
    markets_label = ", ".join(f'{item["city"]}, {item["state"]}' for item in selected_markets)
    top_rows = sorted(fresh, key=lambda item: int(item.get("opportunity_score") or 0), reverse=True)[:10]

    lines = [
        "# Daily Discovery Summary",
        "",
        f"- Run time: {datetime.now(UTC).replace(microsecond=0).isoformat()}",
        f"- Markets covered: {markets_label or 'none'}",
        f"- Niches covered: {', '.join(niches)}",
        f"- New prospects this run: {len(fresh)}",
        f"- Hot prospects this run: {hot}",
        f"- Warm prospects this run: {warm}",
        f"- Total known prospects: {len(all_rows)}",
        "",
        "## New prospects by niche",
        "",
    ]
    for niche, count in sorted(fresh_counter.items()):
        lines.append(f"- {niche}: {count}")
    if not fresh_counter:
        lines.append("- No new prospects discovered")

    lines.extend(["", "## Top fresh prospects", ""])
    for row in top_rows:
        lines.append(
            f"- {row['business_name']} ({row['city']}, {row['state']}) - score {row['opportunity_score']} - {row['website']}"
        )
    if not top_rows:
        lines.append("- No fresh prospects")

    return "\n".join(lines) + "\n"


def main() -> int:
    load_dotenv()
    args = parse_args()

    brave_key = os.getenv("BRAVE_SEARCH_API_KEY", "").strip()
    if not brave_key and not args.dry_run:
        print("BRAVE_SEARCH_API_KEY is required unless --dry-run is used.", file=sys.stderr)
        return 1

    markets = load_markets(args.markets)
    selected_markets = market_slice(markets, args.markets_per_run)
    if not selected_markets:
        print("No markets available.", file=sys.stderr)
        return 1

    planned_queries: list[tuple[str, str, str, str]] = []
    for market in selected_markets:
        city = market["city"]
        state = market["state"]
        for niche in args.niches:
            for query in build_queries(niche, city, state, args.queries_per_market):
                planned_queries.append((niche, city, state, query))

    if args.dry_run:
        for niche, city, state, query in planned_queries:
            print(json.dumps({"niche": niche, "city": city, "state": state, "query": query}))
        return 0

    client, model = build_openai_client(args.ai)
    existing_rows = load_existing_index(args.index)
    seen_domains = {
        (row.get("domain") or root_domain(row.get("resolved_url", "") or row.get("website", "")))
        for row in existing_rows
        if row.get("domain") or row.get("resolved_url") or row.get("website")
    }

    fresh_rows: list[dict[str, str]] = []

    for niche, city, state, query in planned_queries:
        try:
            results = brave_web_search(query, brave_key, args.results_per_query, args.timeout)
        except Exception as exc:  # noqa: BLE001
            print(f"Search failed for {query}: {exc}", file=sys.stderr)
            continue

        for result in results:
            candidate_url = (result.get("url") or "").strip()
            domain = root_domain(candidate_url)
            if not domain or domain in seen_domains or blocked_domain(candidate_url):
                continue
            try:
                row = build_row(result, query, niche, city, state, args.timeout, client, model)
            except Exception as exc:  # noqa: BLE001
                print(f"Skipped {candidate_url}: {exc}", file=sys.stderr)
                continue
            if row is None:
                continue
            seen_domains.add(row["domain"])
            fresh_rows.append(row)

    all_rows = merge_index(existing_rows, fresh_rows)
    schema = list(empty_index_row().keys())
    save_rows(args.index, all_rows, fieldnames=schema)
    save_rows(args.fresh_output, fresh_rows, fieldnames=schema)
    save_rows(args.all_output, all_rows, fieldnames=schema)
    args.summary_output.parent.mkdir(parents=True, exist_ok=True)
    args.summary_output.write_text(summary_markdown(selected_markets, args.niches, fresh_rows, all_rows), encoding="utf-8")

    print(
        json.dumps(
            {
                "markets": selected_markets,
                "queries": len(planned_queries),
                "fresh_prospects": len(fresh_rows),
                "total_prospects": len(all_rows),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
