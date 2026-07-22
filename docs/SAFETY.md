# Safety model — how to let an AI touch a live store

These skills operate on a real store with real money. The design rules that made
that sane, learned by doing it:

## 1. Read-only by default
Audits, keyword pulls, baselines, verification probes — the overwhelming
majority of operations never write anything. A full store audit is 100%
read-only.

## 2. Live changes go draft → human approval → execute
Listing copy is drafted to a file, shown in chat with before/after and char
counts, and **nothing is PATCHed until the user approves the exact text**.
Same for anything buyer-visible. In Claude Code, plan mode is the natural home
for this: propose, approve, then execute.

## 3. Every write is reversible, and the rollback exists BEFORE the write
Pre-edit attributes are saved per SKU (`data/listing_backup_<sku>.json`).
Rollback = re-PATCH the backup. If a change can't be made reversible (rare),
it gets called out explicitly before approval.

## 4. Verify after every write
PATCH accepted ≠ done. Re-read the listing with `includedData=attributes,issues`
and check for new ERROR-severity issues; distinguish new problems from
pre-existing flags. Report exactly what changed and what didn't (Amazon
sometimes silently ignores attributes — warning 90000900).

## 5. Idempotent automation
The review-request script logs every order it touches and skips known ones;
Amazon's own API makes double-sending impossible. Cron jobs can crash, rerun,
or overlap without harm.

## 6. Compliance posture
- Review requests use Amazon's official Solicitations API — the same mechanism
  as Seller Central's "Request a Review" button. No buyer-message workarounds.
- All data access is your own store via your own self-authorized app, plus
  Helium 10's official MCP under your own subscription. Nothing is scraped.
- Credentials live in a gitignored env file on your machine. This repo's
  `.gitignore` covers `config.env` and `data/` — check twice before committing
  anything anyway.

## 7. Know what you CAN'T do (and say so)
Some things have no API path: bullet points on restricted product types
(schema-removed), coupons/deals, removal orders, Helium 10 Keyword Tracker
setup, Brand Registry role changes. The skills surface these as explicit manual
action items instead of pretending. And role/ownership changes (brand-guard)
are never executed by the AI at all — verification yes, mutation no.
