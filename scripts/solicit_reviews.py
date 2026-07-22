#!/usr/bin/env python3
"""Request product reviews for every eligible order via the SP-API Solicitations API.

Amazon allows one review solicitation per order, 5-30 days after delivery.
This script backfills every eligible order in that window and logs results to
data/solicitations_log.json so reruns (e.g. a daily cron/launchd job) skip
orders that were already handled.

Usage:
    python3 solicit_reviews.py --dry-run   # show what would be sent
    python3 solicit_reviews.py             # send for real

Config (config.env): SP_REFRESH_TOKEN, LWA_CLIENT_ID, LWA_CLIENT_SECRET,
SP_REGION, and optionally MARKETPLACE_ID (defaults to US).
"""
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone

from sp_api import SPAPI

HERE = os.path.dirname(os.path.abspath(__file__))
LOG_PATH = os.path.join(HERE, "..", "data", "solicitations_log.json")
SOLICIT_THROTTLE = 1.1  # Solicitations API allows ~1 req/s


def load_log():
    if os.path.exists(LOG_PATH):
        with open(LOG_PATH) as f:
            return json.load(f)
    return {}


def save_log(log):
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "w") as f:
        json.dump(log, f, indent=1, sort_keys=True)


def eligible_orders(sp, marketplace_id):
    """Orders created 5-30 days ago (the solicitation eligibility window)."""
    now = datetime.now(timezone.utc)
    params = {
        "MarketplaceIds": marketplace_id,
        "CreatedAfter": (now - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "CreatedBefore": (now - timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "OrderStatuses": ["Shipped"],
        "MaxResultsPerPage": 100,
    }
    orders = []
    next_token = None
    for _ in range(20):  # hard page cap
        p = {"MarketplaceIds": marketplace_id, "NextToken": next_token} if next_token else params
        resp = sp.get("/orders/v0/orders", params=p)
        payload = resp.get("payload") or resp
        orders.extend(payload.get("Orders", []))
        next_token = payload.get("NextToken")
        if not next_token:
            break
        time.sleep(1)
    return orders


def main():
    dry_run = "--dry-run" in sys.argv
    sp = SPAPI()
    marketplace_id = sp.env.get("MARKETPLACE_ID", "ATVPDKIKX0DER")  # default: US
    log = load_log()
    orders = eligible_orders(sp, marketplace_id)
    print(f"{len(orders)} orders in the 5-30 day window; {len(log)} already in log")

    sent = skipped = ineligible = errors = 0
    for o in orders:
        oid = o["AmazonOrderId"]
        if oid in log:
            skipped += 1
            continue
        try:
            time.sleep(SOLICIT_THROTTLE)
            avail = sp.get(f"/solicitations/v1/orders/{oid}", params={"marketplaceIds": marketplace_id})
            actions = [a.get("name") for a in (avail.get("_links") or {}).get("actions", [])]
            if "productReviewAndSellerFeedback" not in actions:
                log[oid] = {"status": "ineligible", "ts": datetime.now(timezone.utc).isoformat()}
                ineligible += 1
                continue
            if dry_run:
                print(f"  would send: {oid} ({o.get('PurchaseDate', '')[:10]})")
                sent += 1
                continue
            time.sleep(SOLICIT_THROTTLE)
            sp.post(
                f"/solicitations/v1/orders/{oid}/solicitations/productReviewAndSellerFeedback"
                f"?marketplaceIds={marketplace_id}"
            )
            log[oid] = {"status": "sent", "ts": datetime.now(timezone.utc).isoformat()}
            sent += 1
            print(f"  sent: {oid}")
        except Exception as e:
            errors += 1
            print(f"  ERROR {oid}: {e}", file=sys.stderr)

    if not dry_run:
        save_log(log)
    label = "would send" if dry_run else "sent"
    print(f"done: {sent} {label}, {ineligible} ineligible, {skipped} already logged, {errors} errors")


if __name__ == "__main__":
    main()
