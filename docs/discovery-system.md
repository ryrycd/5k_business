# Autonomous Discovery System

## Goal

Keep the prospect list refilling itself without you manually hunting down businesses.

## Design choices

This system is built around:

- low-cost public web discovery
- persistent dedupe
- rotating city coverage
- direct website crawling for contact and fit signals
- daily exports for whatever outreach layer we attach next

## Why this approach

The problem with "free lead lists" is that they usually fail one of these tests:

- illegal or spammy data source
- weak freshness
- no website to audit
- no easy way to keep the list replenished

This setup uses a search API for discovery, then stores only the business-site-derived prospect data. That keeps the saved data focused on what we actually need for outreach and auditing.

## Free-tier budget stance

The defaults are intentionally lean:

- 4 markets per run
- 4 niches
- 1 query per market and niche
- 8 results per query

That keeps the daily search volume low enough to fit a free or near-free discovery budget while still pulling in fresh domains over time.

## Current stack

- `scripts/discover_prospects.py`
- `scripts/run_daily_pipeline.py`
- `data/markets.csv`
- `data/prospect_index.csv`
- `output/fresh-prospects.csv`
- `output/discovered-prospects.csv`
- `output/discovery-summary.md`
- `output/fresh-outreach.csv`

## How rotation works

The script does not hit every city every day.

Instead, it rotates through the markets list based on the UTC day of year. That means:

- daily coverage keeps moving
- query spend stays low
- new business domains continue entering the pipeline over time

## Environment

Add this to `.env`:

```bash
BRAVE_SEARCH_API_KEY=your_key_here
```

Optional:

```bash
OPENAI_API_KEY=your_openai_key
OPENAI_MODEL=gpt-5.4-mini
```

## Run locally

Dry run:

```bash
python3 scripts/discover_prospects.py --dry-run
```

Real run:

```bash
python3 scripts/discover_prospects.py
```

Daily pipeline:

```bash
python3 scripts/run_daily_pipeline.py
```

With AI summaries:

```bash
python3 scripts/discover_prospects.py --ai
```

## Output

`data/prospect_index.csv`

- the rolling master list

`output/fresh-prospects.csv`

- just the new businesses discovered in the latest run

`output/discovered-prospects.csv`

- full export of all known businesses

`output/discovery-summary.md`

- a quick daily summary

`output/fresh-outreach.csv`

- ready-to-send outreach copy for the newest businesses found in the latest run

## Important limitation

This solves discovery and refresh.

It does not make business owners buy automatically by itself. Outreach, deliverability, payment, and trust still matter. But this gets us the machine-fed lead supply the rest of the system needs.
