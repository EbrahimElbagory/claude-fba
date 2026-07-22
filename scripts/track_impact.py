#!/usr/bin/env python3
"""Weekly per-ASIN performance tracker (sessions, conversion, units, revenue).

Pulls the SP-API Sales & Traffic report (child-ASIN granularity) for the
trailing 7 full days and appends one JSON line per run to
data/weekly_tracking.jsonl. Run it weekly (cron/launchd) and diff over time to
see whether listing changes, review growth, or ad pushes actually move numbers.

Usage:
    python3 track_impact.py            # pull last 7 days, append snapshot
    python3 track_impact.py --report   # print first-vs-latest snapshot diff

ASIN scope: put one ASIN per line in data/watch_asins.txt to track a subset;
if the file is missing, every ASIN in the report is tracked.
"""
import json
import os
import sys
from datetime import date, timedelta

from sp_api import SPAPI

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
OUT_PATH = os.path.join(DATA, "weekly_tracking.jsonl")
WATCH_PATH = os.path.join(DATA, "watch_asins.txt")


def watch_list():
    if os.path.exists(WATCH_PATH):
        with open(WATCH_PATH) as f:
            return {l.strip() for l in f if l.strip() and not l.startswith("#")}
    return None  # track everything


def pull_week():
    sp = SPAPI()
    marketplace_id = sp.env.get("MARKETPLACE_ID", "ATVPDKIKX0DER")
    watch = watch_list()
    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=6)
    data = sp.run_report(
        "GET_SALES_AND_TRAFFIC_REPORT",
        [marketplace_id],
        start=start.isoformat(),
        end=end.isoformat(),
        options={"dateGranularity": "WEEK", "asinGranularity": "CHILD"},
    )
    rows = {}
    for r in data.get("salesAndTrafficByAsin", []):
        asin = r.get("childAsin")
        if watch is not None and asin not in watch:
            continue
        sales = r.get("salesByAsin", {})
        traffic = r.get("trafficByAsin", {})
        rows[asin] = {
            "units": sales.get("unitsOrdered", 0),
            "sessions": traffic.get("sessions", 0),
            "cvr_pct": round(traffic.get("unitSessionPercentage", 0.0), 2),
            "revenue": round(sales.get("orderedProductSales", {}).get("amount", 0.0), 2),
        }
    snap = {"week_ending": end.isoformat(), "pulled": date.today().isoformat(), "asins": rows}
    os.makedirs(DATA, exist_ok=True)
    with open(OUT_PATH, "a") as f:
        f.write(json.dumps(snap) + "\n")
    print(f"appended week ending {end}: {len(rows)} ASINs "
          f"({sum(r['units'] for r in rows.values())} units, "
          f"{sum(r['sessions'] for r in rows.values())} sessions)")


def report():
    if not os.path.exists(OUT_PATH):
        print("no weekly snapshots yet - run without --report first")
        return
    with open(OUT_PATH) as f:
        snaps = [json.loads(l) for l in f if l.strip()]
    first, latest = snaps[0], snaps[-1]
    print(f"snapshots: {len(snaps)} (first week ending {first['week_ending']}, "
          f"latest {latest['week_ending']})\n")
    print(f"{'ASIN':12s} {'units':>14s} {'sessions':>14s} {'cvr%':>14s} {'revenue':>16s}")
    for asin in sorted(set(first["asins"]) | set(latest["asins"])):
        a = first["asins"].get(asin, {})
        b = latest["asins"].get(asin, {})
        print(f"{asin:12s} {a.get('units', 0):>5} -> {b.get('units', 0):<5} "
              f"{a.get('sessions', 0):>5} -> {b.get('sessions', 0):<5} "
              f"{a.get('cvr_pct', 0):>5.1f} -> {b.get('cvr_pct', 0):<5.1f} "
              f"{a.get('revenue', 0):>7.0f} -> {b.get('revenue', 0):<7.0f}")


if __name__ == "__main__":
    if "--report" in sys.argv:
        report()
    else:
        pull_week()
