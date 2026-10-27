# Competition Finder

Finds open **case competitions, hackathons and psychology-related comps** on Unstop and Devpost,
keeps only ones whose **final is 15+ days away** with registration still open, ranks them by
organiser (top B-schools, top DU colleges, IITs, companies first — the score decides the order,
the raw organiser name is what's shown), and writes:

- `competitions.xlsx`: sheets for Top Picks / Case Comps / Hackathons / Psychology / All.
  "Days to Reg." and "Days to Final" are live formulas (red ≤3 days, amber ≤7, green after that).
  Type into **Status** (dropdown) and **Notes**. Both are kept every time you re-run.
- `competitions.ics`: Top Picks' registration deadlines (with reminders 3 days and 1 day before) and finals.
  Import it once into Google Calendar (Settings → Import & export) or Outlook.
- A web dashboard (`server.py`) with search, Theme / Source / Mode / Country / Region filters,
  a **Refresh now** button, automatic re-scrape once a day, and download links for the Excel
  and calendar files.

## Files

| File | What it is |
|---|---|
| `scraper.py` | Scrapes Unstop + Devpost, writes `latest.json`, `competitions.xlsx`, `competitions.ics` |
| `server.py` | Dashboard web server on `127.0.0.1:8765` (stdlib only, no framework) |
| `config.py` | All tuning: 15-day rule, theme keywords, organiser scores, Top Picks cut-off |
| `run.bat` | Run the scraper once + open the Excel |
| `start_server.bat` | Start the dashboard in the background (no window) |
| `deploy_spare.bat` | One-shot deploy: deps + dashboard + public Tailscale Funnel URL |
| `AGENT-DEPLOY.md` | Full deployment runbook, written so an AI agent (or a human) can follow it step by step on the server machine |
| `competitions.xlsx` | Latest data snapshot (Status/Notes are preserved across re-runs) |

`latest.json` and `competitions.ics` are generated and git-ignored; the scraper regenerates them.

## Run locally

```
pip install requests openpyxl
python scraper.py      # or double-click run.bat — close Excel first
python server.py       # dashboard at http://127.0.0.1:8765
```

## Deploy to the web (spare laptop as free home server)

Full instructions: **`AGENT-DEPLOY.md`** (it doubles as a handoff doc you can paste to an AI
agent on the target machine — it will take it from fresh install to public URL).

Quick path on the server machine:

1. Put this folder in a **local** path (e.g. `C:\stratgen`) — not OneDrive.
2. Install Python (python.org, tick "Add to PATH") and Tailscale (`winget install Tailscale.Tailscale`),
   sign in to Tailscale with your account.
3. Enable Funnel once in the admin console: console.tailscale.com → DNS → enable Funnel.
4. Double-click `deploy_spare.bat`.
5. It prints your public URL: `https://<node>.<your-tailnet>.ts.net/` — free HTTPS, stable,
   works from any device, no domain needed.

The URL is live only while that machine is on and connected to the internet.

## Tune it

Everything is in `config.py`: the 15-day rule, theme keywords, college/company scores,
the Top Picks cut-off and reminder days.
