"""
Small web dashboard for the competition finder. Serves on localhost only; expose it to your
devices with:  tailscale serve --bg 8765

Run:  python server.py
"""
import html
import json
import subprocess
import sys
import threading
import time
from datetime import date, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import config

HERE = Path(__file__).parent
PORT = 8765
REFRESH_EVERY_HOURS = 24
FILES = {"/competitions.xlsx": ("competitions.xlsx",
                                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
         "/competitions.ics": ("competitions.ics", "text/calendar; charset=utf-8")}

state = {"running": False, "last_log": "", "last_run": None}
lock = threading.Lock()


def run_scraper():
    with lock:
        if state["running"]:
            return
        state["running"] = True
    try:
        p = subprocess.run([sys.executable, str(HERE / "scraper.py")], cwd=HERE,
                           capture_output=True, text=True, encoding="utf-8", timeout=900)
        state["last_log"] = (p.stdout + p.stderr)[-3000:]
    except Exception as e:  # noqa: BLE001
        state["last_log"] = f"Refresh failed: {e}"
    finally:
        state["last_run"] = datetime.now()
        state["running"] = False


def auto_refresh():
    while True:
        snap = HERE / "latest.json"
        age_h = (time.time() - snap.stat().st_mtime) / 3600 if snap.exists() else 1e9
        if age_h >= REFRESH_EVERY_HOURS:
            run_scraper()
        time.sleep(1800)


def days(d):
    return (date.fromisoformat(d) - date.today()).days if d and d != "None" else None


def mode_group(mode):
    low = (mode or "").lower()
    if "hybrid" in low:
        return "Hybrid"
    if "online" in low:
        return "Online"
    if not low or low == "\u2014":
        return "Unknown"
    return "Offline"


# ---------------------------------------------------------------- page
JS = r"""
const rows=[...document.querySelectorAll('tbody tr')];
const el=id=>document.getElementById(id);
const selTheme=el('f-theme'), selSource=el('f-source'), selMode=el('f-mode');
const selCountry=el('f-country'), selRegion=el('f-region'), search=el('f-search');
const countEl=el('count'), resetBtn=el('f-reset');

function fillRegions(){
  const c=selCountry.value;
  const opts=[...new Set(rows.filter(r=>!c || r.dataset.country===c)
                  .map(r=>r.dataset.region).filter(Boolean))].sort();
  const cur=selRegion.value;
  selRegion.innerHTML='<option value="">All regions</option>'+
    opts.map(o=>'<option>'+o+'</option>').join('');
  selRegion.disabled = opts.length===0;
  if(opts.includes(cur)) selRegion.value=cur;
}

function matches(r){
  const t=selTheme.value, s=selSource.value, m=selMode.value;
  const c=selCountry.value, g=selRegion.value, w=search.value.trim().toLowerCase();
  const themeOk = t==='' || (t==='top' ? r.classList.contains('top') : r.dataset.themes.includes(t));
  const srcOk = !s || r.dataset.source===s;
  const modeOk = !m || r.dataset.mode===m;
  const countryOk = !c || r.dataset.country===c;
  const regionOk = !g || r.dataset.region===g;
  const searchOk = !w || r.dataset.search.includes(w);
  return themeOk && srcOk && modeOk && countryOk && regionOk && searchOk;
}

function render(){
  let n=0;
  rows.forEach(r=>{ const ok=matches(r); r.classList.toggle('hidden',!ok); if(ok) n++; });
  countEl.textContent = n+' shown';
}

[selTheme,selSource,selMode,search].forEach(x=>x.addEventListener('input',render));
selCountry.addEventListener('change',()=>{ fillRegions(); render(); });
selRegion.addEventListener('change',render);
resetBtn.addEventListener('click',()=>{
  selTheme.value=''; selSource.value=''; selMode.value='';
  selCountry.value=''; search.value='';
  fillRegions(); selRegion.value=''; render();
});

fillRegions();
render();
"""

STYLE = r"""
:root{--bg:#f7f7f9;--card:#fff;--fg:#1d1d1f;--mut:#6b6b76;--line:#e4e4ea;--acc:#1f3864;--red:#f8cbad;--amber:#ffe699;--top:#eef4ff}
@media (prefers-color-scheme:dark){:root{--bg:#121214;--card:#1c1c20;--fg:#ececf1;--mut:#9a9aa5;--line:#2c2c33;--acc:#8fb0ff;--red:#6b2e22;--amber:#5e4c12;--top:#1a2236}}
body{margin:0;font:14px/1.45 system-ui,-apple-system,Segoe UI,sans-serif;background:var(--bg);color:var(--fg)}
header{padding:16px;display:flex;flex-wrap:wrap;gap:10px;align-items:center;justify-content:space-between}
h1{font-size:20px;margin:0} .mut{color:var(--mut);font-size:13px}
.bar{display:flex;flex-wrap:wrap;gap:8px;padding:0 16px 12px;align-items:center}
button,a.btn{font:inherit;padding:7px 12px;border-radius:8px;border:1px solid var(--line);background:var(--card);color:var(--fg);cursor:pointer;text-decoration:none}
select,input.search{border:1px solid var(--line);border-radius:8px;background:var(--card);color:var(--fg);font:inherit;padding:7px 10px}
select{min-width:120px}
input.search{flex:1;min-width:200px;max-width:380px}
select:disabled{opacity:.5}
.count{color:var(--mut);font-size:13px;margin-left:auto}
.wrap{overflow-x:auto;padding:0 16px 24px}
table{border-collapse:collapse;width:100%;background:var(--card);border:1px solid var(--line);border-radius:10px}
th,td{padding:8px 10px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
th{font-size:12px;color:var(--mut);font-weight:600;white-space:nowrap}
td a{color:var(--acc);font-weight:600;text-decoration:none} .sub{color:var(--mut);font-size:12px}
.num{font-variant-numeric:tabular-nums} tr.top{background:var(--top)} td.red{background:var(--red)} td.amber{background:var(--amber)}
.hidden{display:none!important}
"""

PAGE = r"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Competition Finder</title>
<style>__STYLE__</style></head><body>
<header><div><h1>Competition Finder</h1>
<div class="mut">Updated __UPDATED__ &middot; final &ge; __MINDAYS__ days away &middot; __TOTAL__ open</div></div>
<div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center">
<a class="btn" href="/competitions.xlsx">Excel</a><a class="btn" href="/competitions.ics">Calendar (.ics)</a>
<form method="post" action="/refresh" style="margin:0"><button>Refresh now</button></form></div></header>
<div class="bar" id="f">
<input class="search" id="f-search" placeholder="Search title, organiser, theme..." aria-label="Search competitions">
<select id="f-theme" aria-label="Theme">__THEME_OPTS__</select>
<select id="f-source" aria-label="Source">__SOURCE_OPTS__</select>
<select id="f-mode" aria-label="Mode">__MODE_OPTS__</select>
<select id="f-country" aria-label="Country">__COUNTRY_OPTS__</select>
<select id="f-region" aria-label="Region"></select>
<button id="f-reset">Reset</button>
<span class="count" id="count"></span>
</div>
<div class="wrap"><table><thead><tr><th>Score</th><th>Competition</th><th>Themes</th>
<th>Reg. deadline</th><th>Final</th><th>Mode</th><th>Prize</th><th>Source</th></tr></thead>
<tbody>__ROWS__</tbody></table></div>
<script>__JS__</script></body></html>"""


def _opts(pairs, all_label):
    out = [f'<option value="">{all_label}</option>']
    for val, label in pairs:
        out.append(f'<option value="{html.escape(val)}">{html.escape(label)}</option>')
    return "".join(out)


def render():
    snap = HERE / "latest.json"
    rows = json.loads(snap.read_text(encoding="utf-8")) if snap.exists() else []
    updated = datetime.fromtimestamp(snap.stat().st_mtime).strftime("%d %b %Y, %H:%M") if snap.exists() else "never"
    trs, sources, modes, countries = [], set(), set(), set()
    for r in rows:
        dr, df = days(r["reg_deadline"]), days(r["final_date"])
        if dr is not None and dr < 0:
            continue
        cls = "red" if dr is not None and dr <= 3 else "amber" if dr is not None and dr <= 7 else ""
        top = "top" if r["score"] >= config.TOP_PICK_SCORE else ""
        e = html.escape
        themes = r["themes"]
        country = (r.get("country") or "").strip()
        region = (r.get("region") or "").strip()
        mode = r["mode"] or "\u2014"
        sources.add(r["source"])
        modes.add(mode_group(mode))
        if country not in ("Online", "Offline", "Hybrid", "Unknown"):
            countries.add(country)
        search_blob = e((" ".join([r["title"], r["organiser"], ", ".join(themes)])).lower())
        trs.append(
            f'<tr class="{top}" data-themes="{e(",".join(themes))}" data-source="{e(r["source"])}" '
            f'data-mode="{e(mode_group(mode))}" data-country="{e(country)}" data-region="{e(region)}" '
            f'data-search="{search_blob}">'
            f'<td class="num">{r["score"]}</td>'
            f'<td><a href="{e(r["url"])}" target="_blank" rel="noopener">{e(r["title"])}</a>'
            f'<div class="sub">{e(r["organiser"])}</div></td>'
            f'<td>{e(", ".join(themes))}</td>'
            f'<td class="{cls}">{e(r["reg_deadline"])}<div class="sub">{dr} days</div></td>'
            f'<td>{e(r["final_date"])}<div class="sub">{df} days</div></td>'
            f'<td>{e(mode)}</td><td>{e(r["prize"] or "")}</td><td>{e(r["source"])}</td></tr>')

    theme_pairs = [("top", "Top Picks")] + [(t, t) for t in config.THEMES]
    mode_pairs = [(m, m) for m in ["Online", "Offline", "Hybrid", "Unknown"] if m in modes]
    country_pairs = [(c, c) for c in sorted(countries)]
    source_pairs = [(s, s) for s in sorted(sources)]

    return (PAGE
            .replace("__STYLE__", STYLE)
            .replace("__JS__", JS)
            .replace("__UPDATED__", updated)
            .replace("__MINDAYS__", str(config.MIN_DAYS_TO_FINAL))
            .replace("__TOTAL__", str(len(trs)))
            .replace("__THEME_OPTS__", _opts(theme_pairs, "All themes"))
            .replace("__SOURCE_OPTS__", _opts(source_pairs, "All sources"))
            .replace("__MODE_OPTS__", _opts(mode_pairs, "All modes"))
            .replace("__COUNTRY_OPTS__", _opts(country_pairs, "All countries"))
            .replace("__ROWS__", "".join(trs)))


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in FILES:
            name, ctype = FILES[self.path]
            f = HERE / name
            if not f.exists():
                return self.send_error(404)
            data = f.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Disposition", f'attachment; filename="{name}"')
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            return self.wfile.write(data)
        if self.path not in ("/", "/index.html"):
            return self.send_error(404)
        body = render().encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path != "/refresh":
            return self.send_error(404)
        threading.Thread(target=run_scraper, daemon=True).start()
        self.send_response(303)
        self.send_header("Location", "/")
        self.end_headers()

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    threading.Thread(target=auto_refresh, daemon=True).start()
    print(f"Serving on http://127.0.0.1:{PORT}  (expose with: tailscale serve --bg {PORT})")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
