# Contact Path System

## Purpose

This layer reduces dependence on direct email by detecting contact forms and queuing form submissions automatically.

## What it adds

- `contact_form_url`
- `contact_form_method`
- `contact_form_fields_json`
- `outreach_channel`
- `form_ready` lead state
- `output/form-queue.csv`
- `data/form_log.csv`

## Scripts

- `scripts/generate_audit_pages.py`
- `scripts/submit_contact_forms.py`

## Flow

1. Discovery detects probable contact forms.
2. Lead state marks leads without email but with usable forms as `form_ready`.
3. Audit pages are generated per lead.
4. `submit_contact_forms.py` builds a queue and can optionally submit simple forms live.

## Important limitation

This supports simple HTML forms well enough to automate part of the funnel.

It will not reliably handle:

- complex JavaScript forms
- CAPTCHA-protected forms
- heavily stateful multi-step forms
- anti-bot tooling

That means this layer increases autonomous reach, but it does not eliminate all real-world channel friction.
