# Helium 10 MCP — the market-data half

SP-API tells you about YOUR store. Helium 10's official MCP server adds what
Amazon won't give you: keyword search volumes, competitor ranks, listing quality
scores, CPR, and market-wide estimates. The audit skill uses both.

## Requirements

- A paid Helium 10 plan (the MCP serves real data only on paid tiers).
- Quota: **1,000 MCP tool calls per period** — a full store audit uses ~20–25,
  so weekly audits burn <15% of it.

## Connect

Add the Helium 10 MCP server to Claude Code (Settings → MCP servers, or
`claude mcp add`), endpoint `https://mcp.helium10.com/mcp`. First use triggers
an OAuth flow — approve it in the browser as your Helium 10 login. Tools appear
as `mcp__helium10-mcp__*`.

## The tools the audit actually uses

| Tool | What it gives | Cost tip |
|---|---|---|
| `get_mcp_usage_info` | quota check | free — call first |
| `get_listing_score` | 13-point LQS audit | ONE call scores main + 10 "competitor" ASINs — pass your own catalog |
| `get_top_keywords` | top-10 keyword coverage + ranks | variation siblings share a response — one call per family |
| `get_listing_details` | BSR, reviews, price, est. sales, 30-day BSR history | biggest payload; top sellers only |
| `get_keywords_by_asin` (Cerebro) | every visible keyword | HUGE output — use sparingly |
| `get_search_query_performance` | SQP funnel vs market | Brand Registry only; first call may need ~24h ingestion |
| `list_tracked_keywords`, `get_keywords_rank_history` | daily rank history | only after you populate Keyword Tracker in the H10 UI (no API write) |

## Known quirks (save yourself the debugging)

- `list_my_products` (Profits module) can return empty on healthy accounts —
  source your catalog from SP-API inventory instead.
- Keyword Tracker tools return `no_result` until keywords are added in the UI.
- Historical Cerebro (`time_period`) returns one month per call.

## Works without Helium 10?

Partially. Everything SP-API-side works: review automation, listing edits,
impact tracking, brand verification, sales/traffic analytics. What you lose is
the market layer — keyword volumes, rank tracking, LQS, competitor data.
