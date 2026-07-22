# Setup — SP-API self-authorized app (~30 minutes, one time)

claude-fba talks to Amazon through YOUR own private SP-API app. No third-party
service sees your data; credentials never leave your machine.

## 1. Create the app (Seller Central)

1. Seller Central → **Apps & Services → Develop Apps** (you may need to register
   as a developer first — instant for self-authorization on your own account).
2. **Add new app client**:
   - API type: SP-API
   - Roles: check **Product Listing**, **Pricing**, **Inventory and Order Tracking**,
     **Selling Partner Insights**, **Brand Analytics** (optional), **Direct-to-Consumer Shipping** not needed.
     The features here need: Listings, Orders, Solicitations (part of Order
     Tracking bundle), Reports, A+ (Product Listing).
3. **LWA credentials**: from the app row, "View" → copy **Client ID** and
   **Client Secret**.
4. **Self-authorize**: app row → Authorize → copy the **Refresh Token**
   (long string starting `Atzr|`).

## 2. Configure

```bash
cp scripts/config.example.env scripts/config.env
# fill in LWA_CLIENT_ID, LWA_CLIENT_SECRET, SP_REFRESH_TOKEN
```

## 3. Verify

```bash
python3 scripts/sp_api.py
```

This exchanges the token and probes all three regions, printing your
marketplaces. Set `SP_REGION` and `MARKETPLACE_ID` in `config.env` from its
output. If it prints marketplaces — you're done; everything else in this repo
works from here.

## 4. Point Claude Code at it

Clone this repo, open Claude Code in it, and the `skills/` folder does the rest:

```bash
git clone https://github.com/EbrahimElbagory/claude-fba.git
cd claude-fba && cp -r skills/* .claude/skills/   # or symlink
claude
> audit my store
```

## Troubleshooting

- `403 Unauthorized` on a specific endpoint → the app is missing that role;
  edit the app in Develop Apps, re-check roles, **re-authorize** (new refresh
  token needed after role changes).
- `MD1000`/`invalid grant` on token exchange → refresh token was rotated or the
  app was re-authorized elsewhere; grab a fresh token.
- Auth works but zero marketplaces → the app lacks the Selling Partner Insights
  role.
