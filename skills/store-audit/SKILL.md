---
name: store-audit
description: Full Amazon store audit via Helium 10 MCP + SP-API — listing quality scores, keyword rankings, BSR trends, review health, inventory cover — then diff against stored baselines. Use when the user says "audit my store", "how are my listings doing", "did the changes work", or asks for a weekly/monthly store review.
---

# Store audit → fix → measure loop

Audits the user's whole catalog, compares against saved baselines, and feeds the
other claude-fba skills with prioritized findings.

## Phase 0 — Preconditions
1. Helium 10 MCP connected (OAuth; `mcp__helium10-mcp__*` tools available). A paid
   Helium 10 plan is required for meaningful data.
2. Check quota first: `get_mcp_usage_info` (a full audit uses ~20–25 of the 1,000
   calls/period).
3. Get the catalog: prefer the user's own cached inventory data or SP-API FBA
   inventory (`SPAPI.fba_inventory` in `scripts/sp_api.py`). Note: Helium 10's
   `list_my_products` requires the Profits module to be ingesting — it can return
   empty even on healthy accounts; don't treat that as "no products".

## Phase 1 — Data pull (~20 MCP calls for a 10–20 ASIN catalog)
- `get_listing_score(main_asin=<top seller>, competitor_asins=[up to 10 own ASINs])`
  — ONE call returns the 13-point LQS audit for 11 listings.
- `get_top_keywords(main_asin=X)` per variation-family head — top-10 keyword counts,
  captured search volume, per-keyword organic positions. Siblings in a variation
  family return identical family-level data; don't waste calls on them.
- `get_listing_details(main_asin=X)` for the top ~6 sellers — sub-category BSR,
  reviews, rating, price, estimated sales, 30-day BSR history.
- `get_search_query_performance(...)` if Brand Registered — the impression→click→
  cart→purchase funnel vs. the market per query. First-ever call may return
  DATA_IN_PROGRESS (retry ~24h).
- `list_tracked_keywords` / `get_keywords_rank_history` — only if the user has
  populated Helium 10 Keyword Tracker (no API write exists; setup is manual in the UI).

## Phase 2 — Diff & report
1. Compare against the newest `data/baseline-<date>.json` if one exists.
2. Flag: sub-BSR moves >20 positions, keyword rank drops >5, review/rating changes,
   LQS regressions, week-over-week conversion shifts >2pts (from `track_impact.py`
   snapshots), days-of-cover >180 with Q4 storage-fee season approaching.
3. Write a dated report + save a new baseline JSON with an `interventions` array —
   record every change made and its expected effect so the NEXT audit can attribute.

## Phase 3 — Act (use the sibling skills)
- Copy/keyword fixes → **listing-guard** (draft → user approval → PATCH → backup).
- Review velocity → **review-automation** (backfill + cron health check).
- Measurement → **impact-tracker**.
- Everything not API-executable (bullets on restricted product types, coupons,
  removal orders, tracker setup) → a dated manual-actions list for the user.

## Phase 4 — Data-driven iteration
Once ≥2 baselines exist, recommend from observed deltas (what actually moved
conversion/rank/reviews), not point-in-time heuristics. Scale what worked; kill
what didn't.

## Hard-won gotchas
- Every ASIN may have 2+ SKUs (FBA + FBM offers) — listing-content PATCHes go to
  the BUYABLE one.
- Some product types (e.g. ELECTROSHOCK_WEAPON) have attributes REMOVED from the
  schema (`bullet_point`!) — live content becomes legacy data no API can edit.
  Check the Product Type Definitions API before promising a fix.
- CPR (units needed in 8 days to reach page-1 top half) under ~15 marks a cheap
  ranking push; surface those explicitly.
- Empty `generic_keyword` (backend search terms) is a free, common win — check it
  via the Catalog Items API on every audit.
