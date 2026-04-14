# Quick Start

## Goal

Get from zero to active outreach as fast as possible, without bloating the stack.

## Best first niche

Pick one:

- Roofing
- Plumbing
- HVAC

Do not split attention across multiple offers on day one.

## First 90 minutes

1. Buy or connect a domain.
2. Create a business email inbox.
3. Fill `.env` with your sender identity.
4. Add `BRAVE_SEARCH_API_KEY` to `.env`.
5. Preview `site/index.html` and swap your contact details.

## Prospect sourcing

Default mode:

- let `scripts/discover_prospects.py` generate the list automatically
- rotate through markets daily
- dedupe against `data/prospect_index.csv`

Optional manual mode:

- hand-seed `data/prospects-template.csv` if you find a niche cluster you want to attack immediately

Discovery command:

```bash
python3 scripts/discover_prospects.py
```

## Audit workflow

```bash
python3 scripts/audit_prospects.py data/prospects-template.csv --output output/audits.csv
```

If `OPENAI_API_KEY` is configured:

```bash
python3 scripts/audit_prospects.py data/prospects-template.csv --output output/audits.csv --ai
```

This produces a score plus talking points for each prospect.

If you want the fully automatic path, use the discovery script first and then feed the fresh results into the audit and outreach flow.

## Outreach workflow

```bash
python3 scripts/generate_outreach.py output/audits.csv --output output/outreach.csv
```

With AI enrichment:

```bash
python3 scripts/generate_outreach.py output/audits.csv --output output/outreach.csv --ai
```

## Offer structure

- Setup: `$2,000-$2,500`
- Monthly: `$500-$1,000`
- Pilot option: `7-day install` with limited scope

## Promise

Sell the outcome:

`We install missed-call text-back, instant website lead capture, and basic appointment routing in 24 hours.`

Avoid selling "an AI agent" as the headline.

## What still needs a human

- approving the niche and cities
- connecting accounts
- replying to warm leads
- joining the occasional short close call

## Compliance reminder

Before sending commercial email, make sure your actual email footer includes:

- your real sender identity
- a real mailing address
- an opt-out instruction

If you later use US business texting, complete Twilio/A2P registration before scaling that channel.
