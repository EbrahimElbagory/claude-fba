---
name: keyword-research
description: Amazon keyword research via the Helium 10 MCP — reverse-search competitors (Cerebro), expand seed terms, find coverage gaps, and prioritize by CPR into a keyword map for listings, backend terms, and ad campaigns. Use when the user asks "what keywords should I target", "research keywords for this product", "what do competitors rank for", or before writing/rewriting listing copy.
---

# Keyword research → prioritized keyword map

Discovery is cheap; focus is the product. This skill ends with a per-ASIN keyword
map routed into the other skills — not a 1,500-row dump.

## Inputs
Your ASIN(s), 2–5 competitor ASINs (from `get_listing_details` of your top
keywords' ranking pages, or user-provided), and optionally seed phrases.

## Phase 1 — Discover (pick per goal; watch the quota)
- **Reverse-search a competitor**: `get_keywords_by_asin` (Cerebro) — every phrase
  the ASIN is visible for, with volume, rank, CPC, CPR, title density.
  ⚠ HUGE output (can be 1,000+ rows). Use for 1–2 ASINs max per session and
  summarize immediately; never paste raw output back to the user.
- **Gap vs competitors**: `get_top_keywords(main_asin=yours,
  competitor_asins=[theirs])` — multi mode returns shared keywords + which ones
  competitors rank top-40 for that you don't. This is the highest-signal call
  per token; prefer it over multiple Cerebro pulls.
- **Seed expansion**: `get_keywords_by_keyword("stun gun")` — related phrases
  from a seed when there's no good competitor ASIN yet (new product research).
- **Fresh angles**: `get_keywords_new_suggestion` for terms recently gaining
  volume around an ASIN.
- **Score a finalized list**: `analyze_keywords([...])` — batch metrics for
  candidate lists from any source (brainstorm, PPC search terms, etc.).

## Phase 2 — Filter & prioritize
Score each candidate on:
1. **Volume** — floor of ~300/mo for copy targets; no floor for backend terms.
2. **CPR** — units needed in 8 days for page-1 top half. **CPR ≤ 15 = cheap
   ranking push**; flag these separately, they're the actionable list.
3. **Relevance** — does the phrase describe THIS product? (Ranking for a
   near-miss term brings clicks that don't convert and hurts CVR.)
4. **Trend** — 30-day search-volume trend; a +30%/mo term at 500 volume beats a
   flat 800.
5. **Competition texture** — exact title-match count (low = title opportunity),
   CPC (proxy for commercial intensity).

## Phase 3 — Output: the keyword map (per ASIN)
- **Primary (2–4)**: highest volume × relevance → title + first bullets.
- **Secondary (5–10)**: remaining bullets, description/A+.
- **Backend (~250 bytes)**: everything indexable that doesn't fit copy — no
  brand names, no commas needed, no repeats of title words.
- **Push list**: CPR ≤ 15 terms with current rank 5–20 → hand to ads/promo.
- **Tracker list**: primaries + push list → for the user to add to Helium 10
  Keyword Tracker (UI-only; no API write) so rank history starts accruing.

Route: copy targets → **listing-guard** (draft → approval → PATCH), measurement
→ **impact-tracker** baseline, coverage re-check → next **store-audit**.

## Gotchas (learned in production)
- Variation siblings share keyword data — research the family head, not each child.
- `time_period=YYYY-MM` on Cerebro gives one historical month per call (24-month
  lookback) — useful for seasonality checks before Q4 bets.
- A keyword you rank #6–9 on is worth more than a new one at #80: check current
  rank before chasing volume (get_top_keywords single mode shows your ranks).
- Quota: a focused research session ≈ 5–10 calls of the 1,000/period. The trap
  is Cerebro-ing every competitor "to be thorough" — the gap call usually
  answers the question in one.
