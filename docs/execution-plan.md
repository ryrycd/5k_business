# Lead Rescue AI Execution Plan

## Purpose

This document is the operating blueprint for turning this repo into a functioning automated lead-generation and fulfillment business.

The business goal is:

- reach `$5,000` profit as quickly as possible
- keep setup cost extremely low
- automate as much work as possible
- maintain a self-refreshing lead supply
- make the system robust enough to keep operating with minimal user involvement

This is not a guarantee document. It is the most complete realistic execution plan for the current system.

## What we are building

We are building a productized service business:

**Lead Rescue AI**

Offer:

- missed-call text-back
- instant website lead capture
- lead qualification
- booking or callback routing
- owner alerts
- lightweight follow-up and summary reporting

Target buyers:

- roofing
- plumbing
- HVAC
- water damage / restoration

Core strategy:

- do not wait for organic traffic
- do not build a SaaS first
- generate and score local business leads automatically
- reach out with personalized messages
- close on a high-margin setup fee
- deliver with a repeatable automation stack

## Success definition

### Primary business success

The project succeeds if it does all of the following:

- continuously discovers fresh qualified businesses
- produces outreach-ready copy daily
- creates enough conversations to close at least 2 setup-fee clients
- delivers the service quickly enough that setup-fee revenue becomes real cash, not just interest
- turns first setup clients into recurring monthly clients

### Primary system success

The system succeeds if it does all of the following:

- runs discovery unattended every day
- updates the canonical GitHub repo automatically
- stores and exports fresh prospect data without duplicates
- provides enough signal to prioritize the best businesses
- creates a ready-to-work outreach queue automatically

## Constraints

These constraints govern every decision:

- upfront cash is scarce
- the user should do near-zero manual labor
- the system must be legally defensible
- the system must not rely on ad spend
- the system must keep working when the user is unavailable
- the system must optimize for speed to first cash, not elegance

## Current state

As of this plan:

- repo: `ryrycd/5k_business`
- local `origin` points to that repo
- daily discovery GitHub Action exists
- `BRAVE_SEARCH_API_KEY` has been added as a repo secret
- local discovery has already produced a first batch of live prospects
- a landing page and interactive demo exist
- outreach generation exists
- lead discovery already writes persistent prospect exports

Current working files:

- `scripts/discover_prospects.py`
- `scripts/run_daily_pipeline.py`
- `scripts/generate_outreach.py`
- `site/index.html`
- `site/demo.html`
- `data/prospect_index.csv`
- `output/fresh-prospects.csv`
- `output/fresh-outreach.csv`

## System architecture

### Layer 1: Discovery

Purpose:

- keep the lead list from running dry

Inputs:

- rotating city list
- niche list
- Brave Search API

Outputs:

- `data/prospect_index.csv`
- `output/fresh-prospects.csv`
- `output/discovered-prospects.csv`
- `output/discovery-summary.md`

Current implementation:

- `scripts/discover_prospects.py`

What it does:

- rotates markets by day
- searches niche + city combinations
- filters obvious junk domains
- crawls business websites
- extracts emails and phone numbers where available
- scores opportunity
- creates outreach angles
- dedupes by domain

### Layer 2: Outreach queue generation

Purpose:

- convert fresh prospects into usable outbound work automatically

Inputs:

- `output/fresh-prospects.csv`
- sender identity

Outputs:

- `output/fresh-outreach.csv`

Current implementation:

- `scripts/generate_outreach.py`
- `scripts/run_daily_pipeline.py`

What it does:

- generates subject lines
- creates first email
- creates follow-ups
- creates short call notes

### Layer 3: Sales assets

Purpose:

- give leads a place to land
- provide a demo instead of abstract claims

Current implementation:

- `site/index.html`
- `site/demo.html`
- `docs/sales-assets.md`

What it does:

- frames the offer clearly
- shows pricing options
- demonstrates the workflow visually

### Layer 4: Fulfillment

Purpose:

- deliver fast enough that buyers pay and stay

Current status:

- concept defined
- not fully implemented

Future fulfillment stack:

- Twilio for number + messaging
- OpenAI for intake, qualification, summaries
- Stripe for setup fee + monthly billing
- Google Workspace for sender identity and calendar
- simple database for lead storage and event logs

### Layer 5: Automation hosting

Purpose:

- keep discovery and output refresh running without manual starts

Current implementation:

- `.github/workflows/daily-discovery.yml`

What it does:

- runs the daily pipeline on a schedule
- commits refreshed prospect and outreach outputs back to the repo

## Main business funnel

The business funnel should be understood as five stages:

### Stage 1: discovery

The system finds businesses that:

- have a phone-driven acquisition model
- likely lose leads to missed calls or slow forms
- are in high-ticket service niches
- have weak chat, booking, or instant-response systems

### Stage 2: prioritization

The system should sort leads by:

- opportunity score
- presence of direct email
- simple ownership or office contact path
- urgency-driven verticals
- weak current lead capture

Priority order:

1. high score + direct email
2. high score + phone + contact form
3. warm score + urgent-service niche
4. lower-score leads only if queue volume is low

### Stage 3: outreach

The system should send:

- initial email
- follow-up 1
- follow-up 2

The messaging must emphasize:

- missed leads cost real money
- install is lightweight
- fast setup
- value is visible quickly
- demo is available immediately

### Stage 4: close

The close path should be:

1. prospect replies
2. prospect gets demo or short explanation
3. prospect gets payment link for setup fee or pilot
4. prospect pays
5. onboarding is triggered

### Stage 5: fulfillment

The service is installed fast enough to justify payment:

- basic intake flow
- callback or booking routing
- owner alerts
- reporting

## Revenue model

### Default pricing

- setup fee: `$2,000-$2,500`
- monthly retainer: `$500-$1,000`
- pilot option: `$500`, credited to setup

### Why upfront setup matters

The system is optimized for speed to cash.

That means:

- profit goal is reached with a few sales, not thousands of users
- setup fees matter more than monthly subscriptions in the first phase
- recurring revenue matters more after first validation

### Minimum viable math

Fastest plausible path:

- 2 setup clients at `$2,500`
- gross revenue: `$5,000`
- delivery cost: low
- margin: very high if tooling remains lean

## Execution phases

### Phase 0: stabilize the base

Objective:

- make sure the repo and automation foundation are trustworthy

Must be true:

- GitHub Actions runs successfully with the Brave secret
- output files are committed properly by the workflow
- discovery output quality is acceptable
- local and remote remain in sync

Tasks:

- verify the first scheduled GitHub Action run succeeds
- inspect the action logs
- confirm fresh outputs were updated by GitHub, not just locally
- tighten blocked-domain rules based on junk results
- improve timeouts and retry behavior if the workflow hangs

Definition of done:

- one successful unattended GitHub Actions run
- usable new prospects written to repo automatically

### Phase 1: improve lead quality

Objective:

- make the fresh daily queue more likely to convert

Current risks in discovery:

- large national brands
- directory pages
- supplier pages
- franchise or corporate location pages
- pages with no direct contact path

Tasks:

- expand blocked-domain and blocked-URL logic
- add heuristics for corporate chains
- add direct-email bonus scoring
- add negative scoring for pages without local ownership clues
- optionally add city/service-area detection confidence
- add per-source statistics to the summary report

Definition of done:

- daily queue skews toward true local operators
- fewer junk leads per run
- higher concentration of direct outreach targets

### Phase 2: make outreach actually sendable

Objective:

- convert generated outreach into a real outbound machine

This is the biggest missing operational piece.

Required decisions:

- sending domain
- sender inbox
- sending mechanism
- reply inbox handling

Recommended low-cost path:

- use a dedicated domain or subdomain
- configure Google Workspace or equivalent sender inbox
- send plain-text email in small batches
- store send state locally or in CSV at first

Build tasks:

- create `scripts/send_outreach.py`
- create an outreach state file
- add send throttling and rate limits
- add automatic opt-out suppression
- stop sending to any lead after reply
- write reply labels / statuses back to the repo or a lightweight database

Definition of done:

- daily discovery becomes daily outbound queue
- system can send a modest compliant email volume automatically

### Phase 3: add response handling

Objective:

- prevent replies from becoming a manual bottleneck

Required capabilities:

- classify replies
- separate positive replies from objections and opt-outs
- draft suggested responses
- mark no-send status for opt-outs

Recommended implementation:

- poll inbox or route to webhook
- classify replies with simple rules first
- add AI classification only if needed
- maintain `status` per prospect

Statuses to support:

- new
- queued
- sent_1
- sent_2
- replied_positive
- replied_negative
- bounced
- opted_out
- closed_won
- closed_lost

Definition of done:

- warm leads rise to the top automatically
- obvious dead leads stop consuming attention

### Phase 4: close acceleration

Objective:

- reduce the number of moments where a human must intervene

Build tasks:

- create a short personalized audit page template
- create a payment page / Stripe link flow
- create automated demo links
- create a canned objection handling library
- create a “pilot vs full install” decision tree

Automation goal:

- prospect gets from reply to payment link with minimal manual handling

Definition of done:

- qualified responders can move from interest to payment in one short flow

### Phase 5: fulfillment automation

Objective:

- make delivery fast and consistent enough to support scale

Initial product version:

- missed-call text-back
- website intake widget
- owner alerting
- lead summary

Build tasks:

- create onboarding config template
- store business profile data
- create niche prompt templates
- provision Twilio number and basic routing
- create intake-to-notification workflow
- create weekly summary generator

Definition of done:

- a new client can be provisioned from a single config input

### Phase 6: recurring revenue retention

Objective:

- turn setup wins into monthly retained revenue

Tasks:

- weekly lead summary emails
- monthly value reports
- missed-lead recovery counts
- small workflow tuning
- add-ons like review automation and follow-up sequences

Definition of done:

- clients remain on monthly plans because ROI is visible

## What still requires real-world dependencies

Even with strong automation, some external dependencies cannot be skipped.

These are the biggest ones:

- a real sending domain and inbox
- Stripe account if taking payments online
- Twilio or equivalent for messaging/call workflows
- business identity details for sender trust and compliance
- GitHub Actions secret management

These are not “busywork.” They are the minimum bridge between code and real-world money.

## Compliance and safety requirements

This project should never drift into “spray and pray” spam mode.

Mandatory practices:

- include real sender identity
- include a real mailing address in commercial email
- honor opt-outs
- do not keep emailing after a reply or unsubscribe
- avoid deceptive subjects
- do not send unregistered US business SMS at scale
- keep proof claims honest

Operational rule:

- if a channel becomes compliance-risky, slow down and fix the workflow before scaling it

## KPI dashboard

The system should track these numbers continuously.

### Top-of-funnel KPIs

- markets covered per day
- queries run per day
- new prospects discovered per day
- unique domains added per day
- percent with direct email
- percent marked hot

### Outreach KPIs

- emails queued
- emails sent
- bounce rate
- reply rate
- positive reply rate
- opt-out rate

### Sales KPIs

- demo requests
- payment link visits
- setup fees paid
- pilot conversions
- close rate

### Fulfillment KPIs

- hours from payment to install
- leads captured per client
- weekly summary sent rate
- monthly churn

## Decision rules

These rules keep the project from wandering.

### Niche focus rule

If one niche produces the best reply rate and close rate, concentrate on it instead of distributing effort evenly.

### Channel rule

If outbound email is working, improve it before adding more channels.

### Product rule

If setup fee sales are happening, do not pivot to SaaS or a more complex product.

### Quality rule

If daily lead quality is falling, improve discovery filters before scaling volume.

### Human-effort rule

If a step requires repeated manual work, it becomes a candidate for the next automation sprint.

## What the user should and should not be doing

### User should do as little as possible

The user should only be needed for:

- account ownership where legally required
- payment account setup
- domain/inbox ownership
- occasional approval of high-consequence business decisions

### User should not be doing

- manually building prospect lists
- manually writing outreach one lead at a time
- manually sorting lead quality
- manually checking whether the repo updated

## Codex execution priorities

This is the order Codex should follow in future work.

### Priority 1

- verify unattended GitHub Action success
- tighten discovery quality
- keep `5k_business` as the single source of truth

### Priority 2

- build the automated outbound email layer
- add suppression and status tracking
- make reply handling semi-automatic

### Priority 3

- build payment-link and onboarding flow
- reduce manual close friction

### Priority 4

- build fulfillment automations
- add client reporting

## Repo strategy

Canonical repo:

- `ryrycd/5k_business`

Rules:

- all future code changes from this workspace should push there
- generated outputs that matter for operations should remain versioned
- secrets must never be committed
- `.env` remains local only

Files that should remain tracked:

- code
- docs
- workflow config
- stable generated outputs useful for operations

Files that should remain untracked:

- secrets
- local-only temp artifacts

## Failure modes and mitigations

### Failure mode 1: discovery fills with junk

Mitigation:

- keep expanding blocked-domain rules
- add local-business heuristics
- downrank chains and directories

### Failure mode 2: workflow fails silently

Mitigation:

- inspect Actions logs
- add more explicit logging
- commit summary outputs every run

### Failure mode 3: outreach gets blocked or ignored

Mitigation:

- keep email copy plain
- reduce volume
- personalize more
- improve targeting rather than blasting harder

### Failure mode 4: too much manual sales effort

Mitigation:

- use better demo assets
- use payment links
- standardize objections and responses

### Failure mode 5: fulfillment is too custom

Mitigation:

- narrow the offer
- use templates by niche
- build config-driven onboarding

## Three under-considered risks

These are the three most important things the project was underweighting before this revision.

### 1. Deliverability is a system, not a button

Discovery and outreach generation are not enough if the sending layer performs poorly.

We need to explicitly account for:

- sender domain setup
- SPF, DKIM, and DMARC
- sender reputation
- bounce handling
- warmup strategy
- suppression management
- reply detection
- spam complaint risk

Why this matters:

- a system can appear productive while sending messages that never land in inboxes
- poor sender hygiene can damage the domain and slow the whole business

Required response:

- build the sending layer with state, throttling, and hygiene from the start
- measure deliverability, not just sends

### 2. Trust is the real sales bottleneck

Even highly relevant businesses do not pay setup fees just because the automation is impressive.

We need to explicitly account for:

- business identity trust
- case-study substitutes before real testimonials exist
- clearer proof assets
- guarantee framing
- payment confidence
- objection handling
- a short and credible close flow

Why this matters:

- the biggest drop-off is often between “interested” and “paid”
- a weak trust layer can make a technically strong system underperform

Required response:

- improve demo credibility
- build concise proof and objection assets
- reduce perceived risk before asking for payment

### 3. State management must cover the full funnel

CSV outputs are useful, but they are not yet a complete operational memory system.

We need durable tracking for:

- discovered
- queued
- sent
- bounced
- replied
- opted out
- warm
- closed won
- closed lost
- onboarded
- retained

Why this matters:

- without state, the system can duplicate outreach
- warm leads can get lost
- opt-outs can be mishandled
- follow-up logic becomes unreliable

Required response:

- create a real lead-state model
- make every automation read from and write to that shared state
- treat funnel memory as core infrastructure, not a reporting convenience

## 14-day tactical roadmap

### Day 1

- verify GitHub Action executes with `BRAVE_SEARCH_API_KEY`
- confirm outputs update remotely
- review first live lead batches for junk patterns

### Day 2

- improve discovery filters
- add lead status fields if missing
- define outreach queue ordering

### Day 3

- build outbound email sender script
- add send throttling and suppression list

### Day 4

- test a small outbound batch
- verify send logs and bounce handling

### Day 5

- add reply classification
- surface positive replies automatically

### Day 6

- add Stripe payment link flow
- add payment CTA to landing/demo assets

### Day 7

- add onboarding config template
- create the first fulfillment workflow skeleton

### Day 8 to 10

- improve the demo
- improve close materials
- improve follow-up quality

### Day 11 to 14

- strengthen fulfillment
- add reporting summaries
- prepare recurring-retainer retention layer

## Non-negotiable truths

These truths should guide future decisions:

- discovery alone does not make money
- outreach without deliverability is fake progress
- replies without a close path are wasted
- closed sales without repeatable fulfillment do not scale
- automation should remove repeated work, not hide bad economics

## Recommended next implementation step

The next build target should be:

**automated outbound email sending with state tracking, suppression, and reply-aware queue control**

Why:

- discovery already exists
- the daily queue already exists
- this is the closest missing link between “system runs” and “money starts coming in”

## Operating principle

Every future change should answer this question:

**Does this shorten the path from discovered lead to collected setup fee?**

If not, it is probably not the highest-priority work right now.
