---
name: impact-tracker
description: Capture a pre-intervention baseline of store metrics, snapshot weekly performance (sessions, conversion, units, revenue per ASIN), and diff over time to prove whether changes worked. Use when the user asks "did it work", "track the changes", or before making any batch of store changes.
---

# Measure everything: baseline → intervene → diff

Changes without a baseline are anecdotes. This skill makes every intervention
attributable.

## 1. Baseline BEFORE intervening
Save `data/baseline-<date>.json` with, per ASIN: BSR (category + subcategory),
review count, rating, listing quality score, top-10 keyword count + captured
search volume, key keyword ranks, price, velocity, stock. Plus:
- `interventions`: [] — every change gets appended with {date, action, detail,
  expected_effect}. This is what turns a later diff into attribution.
- `success_criteria_30d`: concrete targets ("ASIN X reviews ≥ 75", "keyword Y
  top-3") the next audit checks mechanically.

## 2. Automated weekly snapshots (SP-API side)
`python3 scripts/track_impact.py` pulls the Sales & Traffic report (child-ASIN
granularity, trailing 7 days) and appends {units, sessions, cvr_pct, revenue}
per ASIN to `data/weekly_tracking.jsonl`. Install
`automation/com.example.track-impact.plist` (Mondays 09:00) or a cron line.
`--report` prints first-vs-latest.

Conversion (unit-session %) is the fastest truth signal: it moves within days
of a listing change, long before rank or reviews do — and it separates traffic
problems (sessions down) from listing problems (conversion down).

## 3. Session-side re-pulls (Helium 10 MCP; needs a Claude session)
Weekly: `get_listing_details` (reviews/rating/BSR) + `get_top_keywords` (rank +
coverage) for the main ASINs. These can't run from cron — the MCP needs an
authenticated session — so pair the automated tracker with a weekly /store-audit.

## 4. Attribution discipline
- Compare against an in-catalog control (an ASIN you did NOT touch) to separate
  seasonality from effect — category-wide dips fool absolute numbers.
- Expected lag: conversion moves in days; backend-keyword indexation in days;
  review counts in 1–3 weeks; organic rank in 2–4 weeks (faster with a
  CPR-sized push).
- Log EVERY intervention (even small ones) in the baseline's `interventions`
  array with a timestamp — future you cannot reconstruct this.
