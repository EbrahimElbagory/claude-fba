#!/usr/bin/env python3
"""Minimal Amazon Ads API client (stdlib only), mirroring sp_api.py conventions.

Setup (one-time):
    1. Create an LWA security profile at developer.amazon.com (Login with Amazon
       console); add http://localhost:8399/ as an Allowed Return URL.
    2. Apply for Ads API access at advertising.amazon.com with that profile.
    3. python3 ads_api.py auth      -> prints consent URL, catches the redirect,
                                       exchanges the code, writes ADS_* to config.env
    4. python3 ads_api.py profiles  -> verify access / list profile ids

Env keys used (config.env): ADS_CLIENT_ID, ADS_CLIENT_SECRET, ADS_REFRESH_TOKEN,
ADS_PROFILE_ID (set after `profiles`).
"""
import http.server
import json
import sys
import time
import urllib.parse
import urllib.request

from sp_api import ENV_PATH, load_env

TOKEN_URL = "https://api.amazon.com/auth/o2/token"
ADS_BASE = "https://advertising-api.amazon.com"
REDIRECT = "http://localhost:8399/"
SCOPE = "advertising::campaign_management"


class AdsAPI:
    def __init__(self, env=None):
        self.env = env or load_env()
        self._token = None
        self._exp = 0

    def access_token(self):
        if self._token and time.time() < self._exp - 60:
            return self._token
        body = urllib.parse.urlencode({
            "grant_type": "refresh_token",
            "refresh_token": self.env["ADS_REFRESH_TOKEN"],
            "client_id": self.env["ADS_CLIENT_ID"],
            "client_secret": self.env["ADS_CLIENT_SECRET"],
        }).encode()
        req = urllib.request.Request(TOKEN_URL, data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.load(resp)
        self._token = data["access_token"]
        self._exp = time.time() + int(data.get("expires_in", 3600))
        return self._token

    def request(self, method, path, body=None, headers=None, profile_id=None):
        h = {
            "Authorization": "Bearer " + self.access_token(),
            "Amazon-Advertising-API-ClientId": self.env["ADS_CLIENT_ID"],
            "Accept": "application/json",
        }
        pid = profile_id or self.env.get("ADS_PROFILE_ID")
        if pid:
            h["Amazon-Advertising-API-Scope"] = str(pid)
        if headers:
            h.update(headers)
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            h.setdefault("Content-Type", "application/json")
        req = urllib.request.Request(ADS_BASE + path, method=method, data=data, headers=h)
        for attempt in range(5):
            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    raw = resp.read()
                    return json.loads(raw) if raw else {}
            except urllib.error.HTTPError as e:
                if e.code in (429, 503) and attempt < 4:
                    time.sleep(2 ** attempt)
                    continue
                raise RuntimeError(f"HTTP {e.code} {method} {path}\n{e.read().decode(errors='replace')}") from None

    def get(self, path, **kw):
        return self.request("GET", path, **kw)

    def post(self, path, body=None, **kw):
        return self.request("POST", path, body=body, **kw)


def _append_env(kv):
    with open(ENV_PATH, "a") as f:
        f.write("\n" + "\n".join(f"{k}={v}" for k, v in kv.items()) + "\n")
    print(f"wrote {', '.join(kv)} to {ENV_PATH}")


def cmd_auth():
    env = load_env()
    cid = env.get("ADS_CLIENT_ID") or input("LWA security profile Client ID: ").strip()
    csec = env.get("ADS_CLIENT_SECRET") or input("Client Secret: ").strip()
    url = "https://www.amazon.com/ap/oa?" + urllib.parse.urlencode({
        "client_id": cid, "scope": SCOPE, "response_type": "code", "redirect_uri": REDIRECT})
    print("\nOpen this URL, log in as the seller account, and approve:\n\n" + url + "\n")
    print("Waiting for the redirect on localhost:8399 ...")
    code_holder = {}

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            code_holder["code"] = (q.get("code") or [None])[0]
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Authorized. You can close this tab.")
        def log_message(self, *a):
            pass

    with http.server.HTTPServer(("localhost", 8399), H) as srv:
        while "code" not in code_holder:
            srv.handle_request()
    body = urllib.parse.urlencode({
        "grant_type": "authorization_code", "code": code_holder["code"],
        "client_id": cid, "client_secret": csec, "redirect_uri": REDIRECT}).encode()
    req = urllib.request.Request(TOKEN_URL, data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        tok = json.load(resp)
    kv = {"ADS_REFRESH_TOKEN": tok["refresh_token"]}
    if not env.get("ADS_CLIENT_ID"):
        kv.update({"ADS_CLIENT_ID": cid, "ADS_CLIENT_SECRET": csec})
    _append_env(kv)


def cmd_profiles():
    api = AdsAPI()
    profs = api.get("/v2/profiles")
    for p in profs:
        print(p.get("profileId"), p.get("countryCode"), p.get("accountInfo", {}).get("type"),
              p.get("accountInfo", {}).get("id"))
    print("\nSet ADS_PROFILE_ID in config.env to the US SELLER profileId above.")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "auth":
        cmd_auth()
    elif cmd == "profiles":
        cmd_profiles()
    else:
        print(__doc__)
