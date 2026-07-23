# claude-fba

**Your Amazon seller ops team in the terminal.** Claude Code skills + a tiny
stdlib-only Python toolkit that turn the Amazon Selling Partner API and the
Helium 10 MCP into an audit → fix → measure loop for your own store.

Built by a seller, on a real store, in production. Day one on mine:

- Full-catalog audit (19 ASINs) — listing quality, keyword ranks, BSR trends — in **~25 API calls**
- **437 review requests** sent via the official Solicitations API (they'd been sitting eligible, unsolicited)
- Found a listing whose bullet points described a **different product** — converting at 2.7% while its siblings did 10–14%
- 4 listings patched (titles + empty backend keywords) with draft → approval → rollback safety
- Baseline captured + weekly tracker installed, so every change is measurable

🌐 **Site:** https://ebrahimelbagory.github.io/claude-fba/ · 📖 [Setup](docs/SETUP.md) · [Helium 10](docs/HELIUM10.md) · [Safety model](docs/SAFETY.md)

## How it works

```
Claude Code (the brain)
 ├── Helium 10 MCP ──── market layer: keyword volumes, ranks, LQS, CPR, competitor data
 ├── SP-API (yours) ─── store layer: listings, orders, solicitations, reports, catalog
 └── launchd/cron ───── keeps review requests + weekly tracking running without you
```

Five skills orchestrate it:

| Skill | What it does |
|---|---|
| [store-audit](skills/store-audit/SKILL.md) | Full checkup of every listing (quality, keywords, rank, reviews, stock) diffed against the last audit |
| [review-automation](skills/review-automation/SKILL.md) | Sends Amazon's official review request for every eligible order, then daily forever |
| [listing-guard](skills/listing-guard/SKILL.md) | Edits live listing text safely: you approve exact wording, old version saved for one-command undo |
| [impact-tracker](skills/impact-tracker/SKILL.md) | Baseline before changes, weekly traffic/conversion/revenue after — proof instead of guessing |
| [keyword-research](skills/keyword-research/SKILL.md) | What competitors rank for that you don't, sorted by how cheap each keyword is to win |

## Install

```bash
git clone https://github.com/EbrahimElbagory/claude-fba.git
cd claude-fba
mkdir -p .claude && cp -r skills .claude/skills
cp scripts/config.example.env scripts/config.env   # fill in your SP-API creds
python3 scripts/sp_api.py                          # verify auth + detect region
claude
> audit my store
```

Requirements: [Claude Code](https://claude.com/claude-code), Python 3.9+ (stdlib
only — zero pip installs), a self-authorized SP-API app
([30-min setup guide](docs/SETUP.md)), and optionally a paid Helium 10 plan for
the market-data layer ([guide](docs/HELIUM10.md)).

## Safety

Live store, real money — so: read-only by default, every buyer-visible change
goes draft → your approval → execute, every write backed up before it happens
and verified after, all through official APIs. Full model: [docs/SAFETY.md](docs/SAFETY.md).

## FAQ

**Is this against Amazon ToS?** No. It's your own store, your own self-authorized
SP-API app, and Amazon's official endpoints — including the same review-request
mechanism as the Seller Central button. Nothing is scraped.

**Do I need Helium 10?** For keyword/rank/market data, yes (paid plan; their MCP
is official). Everything SP-API-side — review automation, listing edits, impact
tracking, sales analytics — works without it.

**What does it cost to run?** Claude Code subscription + optionally Helium 10.
The scripts themselves are free, stdlib-only, and run on a laptop.

**Windows?** The scripts and skills work anywhere Python does; the two
`automation/` templates are macOS launchd — use Task Scheduler/cron equivalents.

## License

MIT — [Ebrahim Elbagory](https://github.com/EbrahimElbagory)
