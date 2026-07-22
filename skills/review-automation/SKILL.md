---
name: review-automation
description: Backfill Amazon review requests for every eligible order via the SP-API Solicitations API and keep a daily job running. Use when the user says "request reviews", "set up review automation", "why do I have so few reviews", or during a store audit that finds low review velocity.
---

# Review-request automation (Solicitations API)

Amazon lets you request a review ONCE per order, 5–30 days after delivery, via
the official Solicitations API — identical to Seller Central's "Request a Review"
button, but scriptable. Most sellers never systematize this; a store doing
~500 orders/month forgoes thousands of asks per year.

## One-time backfill
1. Verify API access (read-only probe): fetch one recent order via
   `GET /orders/v0/orders`, then `GET /solicitations/v1/orders/{id}` — if
   `productReviewAndSellerFeedback` appears in `_links.actions`, the app has the
   Solicitations role and orders are waiting.
2. `python3 scripts/solicit_reviews.py --dry-run` — counts eligible orders,
   sends nothing. Show the user the count and get an explicit go.
3. `python3 scripts/solicit_reviews.py` — sends for real. ~1 req/s throttle;
   a 400-order backfill takes ~15 min. Results log to
   `data/solicitations_log.json` (dedupe store — reruns skip known orders).
4. Verify dedupe: immediately rerun → expect "0 sent, N already logged".

## Keep it running
- Install `automation/com.example.solicit-reviews.plist` (macOS launchd, daily
  10:00; runs on wake if the machine was asleep). Linux: equivalent cron line
  `0 10 * * * python3 /path/to/scripts/solicit_reviews.py`.
- Health check on every audit: job loaded (`launchctl list | grep solicit`),
  log fresh (<48h), log growing.

## Notes & guardrails
- Sending is idempotent-safe: once sent, the action disappears from `_links.actions`
  and the order logs as ineligible — no duplicate emails possible.
- This is Amazon's own compliant mechanism. Do NOT combine with manual buyer
  messaging asking for reviews (that path has ToS landmines; this one doesn't).
- Expect effects in review counts 1–3 weeks after the backfill; measure with
  impact-tracker + the audit's review-count diff, and expect roughly a
  3–5% request→review conversion.
