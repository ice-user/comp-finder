# Deployment Handoff — Competition Finder

You are taking over a deployment task on **this machine** (a spare Windows laptop that will be
left powered on at home). Read this document completely before doing anything. The owner has
already verified the project runs; your job is to make it publicly reachable over the web,
for free, with no domain.

## Mission

End state: a public HTTPS URL of the form `https://<this-machine>.<tailnet>.ts.net/`
serving the Competition Finder dashboard to anyone on the internet. No router changes,
no port forwarding, no public inbound ports, no paid services.

## Facts about the project (verified — do not re-derive by guessing)

- Language: Python 3 (tested on 3.14; any recent 3.x works).
- Dependencies: `requests`, `openpyxl`. Nothing else.
- `server.py`: stdlib `http.server` dashboard. Binds **127.0.0.1:8765 only**.
  That bind address is deliberate — the tunnel proxies to localhost, so keep it.
- `scraper.py`: fetches Unstop + Devpost (plain `requests.get`, no auth, no cookies),
  writes `latest.json`, `competitions.xlsx`, `competitions.ics` next to itself.
  A single run takes a few minutes.
- `server.py` auto-runs the scraper on start if `latest.json` is missing or >24h old,
  and exposes `POST /refresh` (the "Refresh now" button) that re-runs it.
  Assume anyone on the internet can trigger a scrape. That is accepted by the owner.
- No API keys, no credentials, no secrets anywhere in the repo. The data served is
  public competition information. Safe to expose.
- `competitions.xlsx` in the repo is a data snapshot; the scraper preserves its
  Status/Notes columns across re-runs.

## Hard rules

1. Work from a **local** folder (e.g. `C:\stratgen`). Never run the server from
   OneDrive, Dropbox or any sync folder — the server rewrites output files daily and
   sync conflicts/file locks will break it.
2. Do not port-forward, do not touch the home router, do not change the server's
   bind address to 0.0.0.0.
3. Do not start the public tunnel until the local server returns HTTP 200
   on `http://127.0.0.1:8765`.
4. Do not modify `server.py` or `scraper.py` for deployment purposes.
5. If a step needs a human action (signing into a website), hand it to the user
   verbatim and wait — do not guess credentials or click through on their behalf.

## Steps

Each step has a **gate**: verify the stated evidence before moving on. If a gate fails,
go to "If it fails" at the bottom.

### 0. OS check
- Gate: this is Windows (check `ver`). If it's Linux instead, adapt mechanically
  (winget → system package manager, `pythonw` → `nohup`, Startup folder → systemd
  service, `taskkill` → `pkill`) and keep the same gates.

### 1. Python
- Command: `python --version`
- If missing: install from python.org, **tick "Add python.exe to PATH"** during setup.
- Gate: prints a 3.x version.

### 2. Dependencies
- Command: `python -m pip install --disable-pip-version-check requests openpyxl`
- Gate: exit 0 (already-satisfied is fine).

### 3. Local sanity run
- Run `python server.py` in a terminal; in a second terminal:
  `curl -s -o NUL -w "%{http_code}" http://127.0.0.1:8765`
- Gate: prints `200`. (Windows `curl` writes to NUL, not /dev/null.)
- Then stop it (Ctrl+C) — it restarts headless in step 7.

### 4. Tailscale installed + logged in
- Command: `where tailscale` → if missing: `winget install Tailscale.Tailscale`
- Command: `tailscale status`
- Gate: it succeeds AND lists the node `laptop-qmae9p40` (the owner's main laptop,
  same tailnet). If it prompts for login: that's interactive — ask the user to sign in
  via the Tailscale app with their existing account (the one that owns the tailnet that
  contains `laptop-qmae9p40`). Wrong account = different tailnet = wrong URL.

### 5. Give this machine a stable name (once)
- Command: `tailscale up --hostname=stratgen-server`
  (or ask the user what name they want; the public URL uses it).
- Gate: `tailscale status --self` shows the new name.
- Expected final URL: `https://stratgen-server.<tailnet>.ts.net/` where `<tailnet>`
  is the tailnet name shown in `tailscale status` output / console (e.g. `taila24302`).

### 6. Enable Funnel (one-time, human action)
- If not already enabled: console.tailscale.com → **DNS** page → enable **Funnel**.
  Ask the user to do it (needs their account) and wait.
- Gate: none directly — proven by step 8.

### 7. Start the service headless
- Command: `start "" pythonw server.py` (or double-click `start_server.bat`).
- Gate: `curl -s -o NUL -w "%{http_code}" http://127.0.0.1:8765` prints `200`
  (wait ~5 s after starting; first run may take longer while it scrapes — the
  dashboard itself still serves, showing "Updated never" until the first
  scrape finishes).

### 8. Open the public tunnel
- Command: `tailscale funnel --bg 8765 --yes`
  (`--bg` = background + persists across reboots; the Tailscale service itself
  auto-starts with Windows, so after this, reboots are self-healing.)
- Gate: `tailscale funnel status` shows a line like
  `https://stratgen-server.<tailnet>.ts.net` with
  `|-- / proxy http://127.0.0.1:8765` and **no** "(tailnet only)" tag.
  "(tailnet only)" means `serve` is active for that port instead — re-run the
  funnel command; the last command to configure the port wins.

### 9. Public verification (mandatory)
- The URL must be checked from **outside the tailnet** — any Tailscale device can
  reach it, so a local check proves nothing.
- Ask the user to open `https://stratgen-server.<tailnet>.ts.net/` in a browser on
  a phone using **mobile data** (Wi-Fi off).
- Gate: the page shows the "Competition Finder" header, a competition table (or
  "Updated never" while the first scrape runs), and working Excel / Calendar
  download buttons.

### 10. Always-on configuration
- Settings → System → Power: sleep (plugged in) = **Never**; battery = Never if it
  will ever run unplugged.
- Settings → Power → "When I close the lid" (or Control Panel → Power Options) =
  **Do nothing**.
- Tell the user explicitly: the URL only works while this laptop is on,
  logged in, and connected to the internet.

### 11. Auto-start after reboot
- `shell:startup` (Win+R) → create a shortcut to `start_server.bat` in that folder.
- The funnel and Tailscale service persist on their own (step 8's `--bg`);
  only the Python app needs this shortcut.

## If it fails

| Symptom | Cause / fix |
|---|---|
| Local curl: connection refused | Server not running. Run `python server.py` in the foreground and read the error — almost always a missing dep (step 2) or a stale `python` pointing at the wrong install. |
| `tailscale funnel` error about Funnel not enabled | Step 6 not done (admin console toggle, human action). |
| `tailscale status` fails / lists no familiar nodes | Not logged in, or logged in with the wrong account (step 4). |
| URL dead from phone, fine locally | Machine asleep or offline. Check `tailscale status` from the owner's main laptop: this node must read `online`. |
| Port 8765 already in use | `netstat -ano \| findstr :8765` → kill the listed PID (or `taskkill /f /im pythonw.exe`). |
| First page load shows "Updated never" for minutes | Normal: first scrape takes a few minutes; it auto-runs on start. |

## Stopping / teardown

- Stop public access (server keeps running locally): `tailscale funnel --https=443 off`
- Stop the dashboard: `taskkill /f /im pythonw.exe`
- Remove the machine from the tailnet later: admin console → machine → delete.

## Definition of done

All of these true, then report the final URL to the user:

- [ ] `http://127.0.0.1:8765` → HTTP 200 locally
- [ ] `tailscale funnel status` shows the public URL proxying `127.0.0.1:8765`
- [ ] User confirmed the URL opens on a non-Tailscale device (phone, mobile data)
- [ ] Sleep disabled, lid-close = do nothing, startup shortcut installed
- [ ] User told: URL is live only while the laptop is on and online
