---
name: listing-guard
description: Edit live Amazon listing content (titles, backend keywords, attributes) via the SP-API Listings Items API with a draft → user-approval → PATCH → backup/rollback flow. Use when the user wants listing copy fixed, titles extended, backend search terms filled, or an audit found content problems.
---

# Listing edits with a safety harness

Live listings are live money. This skill's contract: **nothing changes on Amazon
without the user approving the exact copy first**, and every change is reversible.

## The flow
1. **Map ASIN → SKU.** `GET /listings/2021-08-01/items/{sellerId}` (search by
   seller). Each ASIN often has multiple SKUs (FBA + FBM offers) — content
   patches target the **BUYABLE** SKU.
2. **Read current state from two places:**
   - Seller contribution: `GET .../items/{sellerId}/{sku}?includedData=attributes,productTypes`
   - Live reconciled view: `GET /catalog/2022-04-01/items/{asin}?includedData=attributes`
   These can differ (old contributions, content from other sources). The catalog
   view is what buyers see — treat it as the "before".
3. **Check the schema before promising anything.** Product Type Definitions API:
   `GET /definitions/2020-09-01/productTypes/{type}?requirements=LISTING` → fetch
   the schema JSON and confirm the attribute you want to edit EXISTS. Restricted
   categories have attributes removed (real example: `bullet_point` is gone from
   ELECTROSHOCK_WEAPON — bullets there are legacy data no API or flat file can
   touch; only a Seller Central case can).
4. **Draft.** Write new copy to a drafts file with before/after and char counts.
   Targets that keep listing-quality checkers happy: title 150–200 chars, bullets
   ≥150 chars each, no all-caps words, no symbols/emojis, keyword-bearing but human.
   Backend `generic_keyword` ≤ ~250 bytes, no commas needed, no brand names.
5. **STOP — show the user the drafts in chat and wait for approval.**
6. **Back up, then PATCH.** Save the current attributes JSON per SKU
   (`data/listing_backup_<sku>.json`), then:
   ```
   PATCH /listings/2021-08-01/items/{sellerId}/{sku}?marketplaceIds={mp}
   {"productType": "<TYPE>", "patches": [
     {"op":"replace","path":"/attributes/item_name",
      "value":[{"value":"...","language_tag":"en_US","marketplace_id":"<mp>"}]},
     {"op":"replace","path":"/attributes/generic_keyword","value":[...]}]}
   ```
7. **Verify.** Response should be ACCEPTED with a submissionId. Re-GET with
   `includedData=attributes,issues`: the new values stored, and no NEW
   ERROR-severity issues (pre-existing issues, e.g. image-compliance flags, are
   not yours — but report them). Amazon publishes in minutes–hours.

## Rollback
Re-PATCH with the values from `data/listing_backup_<sku>.json`. That's the whole
procedure — which is why step 6's backup is non-negotiable.

## Watch for in responses
- Warning 90000900 "attribute does not belong to the product type … ignoring" —
  your edit for that attribute was silently dropped; check the schema (step 3).
- Issue 100581 (main image contains text/logo) — pre-existing compliance flag
  worth surfacing to the user even though it's not content you touched.
