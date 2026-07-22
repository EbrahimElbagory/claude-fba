"""Minimal Amazon SP-API client (stdlib only).

No AWS signing required (Amazon dropped SigV4 in 2024) — auth is pure LWA:
exchange the long-lived refresh token for a short-lived access token, then send
it as the `x-amz-access-token` header on each SP-API request.

Credentials load from config.env (gitignored). Nothing here is secret.
"""

import json
import os
import time
import urllib.parse
import urllib.request
import urllib.error

ENV_PATH = os.environ.get("CLAUDE_FBA_CONFIG") or os.path.join(os.path.dirname(__file__), "config.env")

REGION_ENDPOINTS = {
    "na": "https://sellingpartnerapi-na.amazon.com",
    "eu": "https://sellingpartnerapi-eu.amazon.com",
    "fe": "https://sellingpartnerapi-fe.amazon.com",
}
LWA_TOKEN_URL = "https://api.amazon.com/auth/o2/token"


def load_env(path=ENV_PATH):
    """Tiny .env parser: KEY=VALUE, ignores comments, strips quotes/inline comments."""
    env = {}
    if not os.path.exists(path):
        raise SystemExit(
            f"No config found at {path}.\n"
        "Copy scripts/config.example.env to scripts/config.env and fill in your "
        "SP-API credentials (see docs/SETUP.md)."
        )
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip()
            # strip surrounding single/double quotes
            if len(val) >= 2 and val[0] in "'\"" and val[-1] == val[0]:
                val = val[1:-1]
            else:
                # drop trailing inline comment for unquoted values (e.g. "na   # ...")
                val = val.split("#", 1)[0].strip()
            env[key] = val
    return env


class SPAPI:
    def __init__(self, env=None):
        self.env = env or load_env()
        self.region = (self.env.get("SP_REGION") or "na").strip()
        self.base = REGION_ENDPOINTS[self.region]
        self._access_token = None
        self._token_exp = 0

    # --- auth -----------------------------------------------------------------
    def access_token(self):
        if self._access_token and time.time() < self._token_exp - 60:
            return self._access_token
        body = urllib.parse.urlencode({
            "grant_type": "refresh_token",
            "refresh_token": self.env["SP_REFRESH_TOKEN"],
            "client_id": self.env["LWA_CLIENT_ID"],
            "client_secret": self.env["LWA_CLIENT_SECRET"],
        }).encode()
        req = urllib.request.Request(
            LWA_TOKEN_URL, data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.load(resp)
        self._access_token = data["access_token"]
        self._token_exp = time.time() + int(data.get("expires_in", 3600))
        return self._access_token

    # --- generic request ------------------------------------------------------
    def request(self, method, path, params=None, body=None, base=None):
        url = (base or self.base) + path
        if params:
            url += "?" + urllib.parse.urlencode(params, doseq=True)
        headers = {
            "x-amz-access-token": self.access_token(),
            "accept": "application/json",
        }
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            headers["content-type"] = "application/json"
        req = urllib.request.Request(url, method=method, data=data, headers=headers)
        for attempt in range(5):
            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    raw = resp.read()
                    return json.loads(raw) if raw else {}
            except urllib.error.HTTPError as e:
                if e.code in (429, 503) and attempt < 4:
                    time.sleep(2 ** attempt)          # 1,2,4,8s backoff
                    continue
                detail = e.read().decode(errors="replace")
                raise RuntimeError(f"HTTP {e.code} {method} {path}\n{detail}") from None

    def get(self, path, params=None, base=None):
        return self.request("GET", path, params=params, base=base)

    def post(self, path, body=None, base=None):
        return self.request("POST", path, body=body, base=base)

    # --- convenience endpoints ------------------------------------------------
    def marketplace_participations(self, base=None):
        return self.get("/sellers/v1/marketplaceParticipations", base=base)

    # --- Reports API (2021-06-30) ---------------------------------------------
    def create_report(self, report_type, marketplace_ids, start=None, end=None, options=None):
        body = {"reportType": report_type, "marketplaceIds": marketplace_ids}
        if start:
            body["dataStartTime"] = start
        if end:
            body["dataEndTime"] = end
        if options:
            body["reportOptions"] = options
        return self.post("/reports/2021-06-30/reports", body=body)["reportId"]

    def get_report(self, report_id):
        return self.get(f"/reports/2021-06-30/reports/{report_id}")

    def list_reports(self, report_types, created_since=None, page_size=100, max_pages=30):
        """List already-generated reports (e.g. auto-scheduled settlement reports)."""
        reports = []
        params = {"reportTypes": report_types, "pageSize": page_size}
        if created_since:
            params["createdSince"] = created_since
        next_token = None
        for _ in range(max_pages):
            call = {"nextToken": next_token} if next_token else params
            data = self.get("/reports/2021-06-30/reports", params=call)
            payload = data.get("payload", data)
            reports.extend(payload.get("reports", []))
            next_token = payload.get("nextToken")
            if not next_token:
                break
            time.sleep(0.5)
        return reports

    def get_report_document(self, document_id):
        return self.get(f"/reports/2021-06-30/documents/{document_id}")

    def poll_report(self, report_id, interval=5, timeout=300):
        """Block until the report finishes; return its metadata."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            meta = self.get_report(report_id)
            status = meta.get("processingStatus")
            if status in ("DONE", "FATAL", "CANCELLED"):
                return meta
            time.sleep(interval)
        raise TimeoutError(f"Report {report_id} not done after {timeout}s")

    @staticmethod
    def download_document(doc):
        """Fetch a report document from its presigned URL; gunzip if needed."""
        import gzip
        with urllib.request.urlopen(doc["url"], timeout=120) as resp:
            raw = resp.read()
        if doc.get("compressionAlgorithm") == "GZIP":
            raw = gzip.decompress(raw)
        return raw.decode("utf-8", errors="replace")

    # --- FBA Inventory + Pricing ----------------------------------------------
    def fba_inventory(self, marketplace_id, max_pages=100):
        """All FBA inventory summaries (units on hand / inbound / reserved)."""
        items = []
        params = {
            "details": "true",
            "granularityType": "Marketplace",
            "granularityId": marketplace_id,
            "marketplaceIds": marketplace_id,
        }
        next_token = None
        for _ in range(max_pages):
            call = dict(params)
            if next_token:
                call["nextToken"] = next_token
            data = self.get("/fba/inventory/v1/summaries", params=call)
            payload = data.get("payload", {})
            items.extend(payload.get("inventorySummaries", []))
            next_token = (data.get("pagination") or {}).get("nextToken")
            if not next_token:
                break
            time.sleep(0.6)
        return items

    def get_pricing(self, asins, marketplace_id):
        """Current price info for up to 20 ASINs per call."""
        out = []
        for i in range(0, len(asins), 20):
            batch = asins[i:i + 20]
            data = self.get("/products/pricing/v0/price", params={
                "MarketplaceId": marketplace_id,
                "Asins": batch,
                "ItemType": "Asin",
            })
            out.extend(data.get("payload", []))
            time.sleep(0.6)
        return out

    # --- Finances API (2024-06-19) transactions -------------------------------
    def transactions(self, posted_after, posted_before=None, marketplace_id=None, max_pages=400):
        """All financial transactions in a window, paginated."""
        txns = []
        params = {"postedAfter": posted_after}
        if posted_before:
            params["postedBefore"] = posted_before
        if marketplace_id:
            params["marketplaceId"] = marketplace_id
        next_token = None
        for _ in range(max_pages):
            call = {"nextToken": next_token} if next_token else params
            data = self.get("/finances/2024-06-19/transactions", params=call)
            payload = data.get("payload", data)
            txns.extend(payload.get("transactions", []))
            next_token = payload.get("nextToken")
            if not next_token:
                break
            time.sleep(0.6)
        # dedupe: pagination can return overlapping/repeated records
        seen, unique = set(), []
        for t in txns:
            key = json.dumps(t, sort_keys=True)
            if key not in seen:
                seen.add(key)
                unique.append(t)
        return unique

    # --- Finances API (v0) ----------------------------------------------------
    def financial_event_groups(self, started_after=None, started_before=None, max_pages=200):
        """All financial event groups (settlement/payout periods), paginated."""
        groups = []
        params = {"MaxResultsPerPage": 100}
        if started_after:
            params["FinancialEventGroupStartedAfter"] = started_after
        if started_before:
            params["FinancialEventGroupStartedBefore"] = started_before
        next_token = None
        for _ in range(max_pages):
            call = {"NextToken": next_token} if next_token else params
            data = self.get("/finances/v0/financialEventGroups", params=call)
            payload = data.get("payload", {})
            groups.extend(payload.get("FinancialEventGroupList", []))
            next_token = payload.get("NextToken")
            if not next_token:
                break
            time.sleep(1.2)  # ~0.5 rps limit
        return groups

    def run_report(self, report_type, marketplace_ids, start=None, end=None, options=None):
        """One-shot: create → poll → download → return parsed content."""
        rid = self.create_report(report_type, marketplace_ids, start, end, options)
        meta = self.poll_report(rid)
        if meta.get("processingStatus") != "DONE":
            raise RuntimeError(f"Report {rid} ended {meta.get('processingStatus')}: {meta}")
        doc = self.get_report_document(meta["reportDocumentId"])
        text = self.download_document(doc)
        try:
            return json.loads(text)          # JSON reports (e.g. Sales & Traffic)
        except json.JSONDecodeError:
            return text                       # tab-delimited flat-file reports


if __name__ == "__main__":
    sp = SPAPI()
    print("Region configured:", sp.region)
    print("Verifying auth (LWA token exchange)...")
    tok = sp.access_token()
    print("  access token acquired:", tok[:12], "...\n")

    # marketplaceParticipations is region-specific; probe all three so we don't
    # need the user to know their region up front.
    found = None
    for region, base in REGION_ENDPOINTS.items():
        try:
            data = sp.marketplace_participations(base=base)
            parts = data.get("payload", [])
            if parts:
                print(f"[{region}] {len(parts)} marketplace(s):")
                for p in parts:
                    m = p.get("marketplace", {})
                    part = p.get("participation", {})
                    print(f"  - {m.get('name')} | id={m.get('id')} | "
                          f"country={m.get('countryCode')} | currency={m.get('defaultCurrencyCode')} | "
                          f"selling={part.get('isParticipating')}")
                found = region
                break
            else:
                print(f"[{region}] auth ok but 0 marketplaces")
        except RuntimeError as e:
            first = str(e).splitlines()[0]
            print(f"[{region}] {first}")

    if found:
        print(f"\n==> Your store lives in region '{found}'. "
              f"Set SP_REGION={found} in config.env and add the marketplace id above.")
    else:
        print("\nNo marketplaces returned in any region — auth worked but the app "
              "may lack the Selling Partner Insights role, or the token needs re-authorizing.")
