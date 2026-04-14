# Lead Rescue AI Starter Kit

This workspace is the execution package for a fast-cash local-service automation business.

The core play is simple:

- sell a missed-call recovery + lead capture system
- charge upfront setup fees
- automate research, outreach, onboarding, and reporting

Start here:

1. Read [fast-roi-plan.md](./fast-roi-plan.md).
2. Read [docs/quick-start.md](./docs/quick-start.md).
3. Read [docs/discovery-system.md](./docs/discovery-system.md).
4. Preview the offer page in [site/index.html](./site/index.html).
5. Use [data/prospects-template.csv](./data/prospects-template.csv) only if you want to hand-seed prospects.

## Workspace layout

- `site/` marketing page and interactive demo
- `scripts/` audit and outreach generation scripts
- `data/` CSV templates
- `output/` generated CSV and markdown files
- `docs/` runbook and sales assets

## Local setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Main commands

Discover fresh prospects automatically:

```bash
python3 scripts/discover_prospects.py
```

Run the daily discovery + outreach queue pipeline:

```bash
python3 scripts/run_daily_pipeline.py
```

Dry run to inspect the rotating query plan:

```bash
python3 scripts/discover_prospects.py --dry-run
```

Score and audit prospects:

```bash
python3 scripts/audit_prospects.py data/prospects-template.csv --output output/audits.csv
```

Generate outreach copy from audits:

```bash
python3 scripts/generate_outreach.py output/audits.csv --output output/outreach.csv
```

Run with AI enrichment after adding `OPENAI_API_KEY`:

```bash
python3 scripts/audit_prospects.py data/prospects-template.csv --output output/audits.csv --ai
python3 scripts/generate_outreach.py output/audits.csv --output output/outreach.csv --ai
```

Preview the site locally:

```bash
python3 -m http.server 8000
```

Then open `http://localhost:8000/site/`.
