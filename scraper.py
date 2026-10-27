"""
Competition finder: pulls open case competitions, hackathons and psychology-related
competitions from Unstop and Devpost, ranks them by organiser prestige, and writes
competitions.xlsx plus a calendar file (competitions.ics) with deadline reminders.

Run:  python scraper.py
"""
import html
import json
import re
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import requests
from openpyxl import Workbook, load_workbook
from openpyxl.formatting.rule import CellIsRule, FormulaRule
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

import config

HERE = Path(__file__).parent
XLSX = HERE / "competitions.xlsx"
ICS = HERE / "competitions.ics"
SNAPSHOT = HERE / "latest.json"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/130 Safari/537.36",
    "Accept": "application/json",
}
TODAY = date.today()
MIN_FINAL = TODAY + timedelta(days=config.MIN_DAYS_TO_FINAL)


# ---------------------------------------------------------------- helpers
def kw_regex(words):
    """Whole-word-ish match so 'itc' doesn't hit 'Switch' and 'meta' doesn't hit 'Metal'."""
    parts = [r"(?<![a-z0-9])" + re.escape(w.strip().lower()) for w in words]
    return re.compile("|".join(parts))


THEME_RX = {name: kw_regex(words) for name, words in config.THEMES.items()}
PRESTIGE_RX = [(re.compile(r"(?<![a-z0-9])" + re.escape(k) + r"(?![a-z0-9])"), label, score)
               for k, label, score in config.PRESTIGE]
CORP_RX = re.compile("|".join(r"(?<![a-z0-9])" + re.escape(c.strip()) + r"(?![a-z0-9])"
                              for c in config.CORPORATES))
NOT_CORP_RX = kw_regex(config.NOT_CORPORATE)
COLLEGE_RX = re.compile(r"college|university|institute|school|vidyalaya|iit|nit|academy|campus")


def strip_html(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def parse_dt(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s).date()
    except ValueError:
        return None


# ---------------------------------------------------------------- location
# Map a free-text Devpost location ("Austin, TX, USA") to (country, region).
_COUNTRIES = {
    "usa": "USA", "u.s.a.": "USA", "united states": "USA", "us": "USA",
    "united states of america": "USA",
    "canada": "Canada", "india": "India", "singapore": "Singapore",
    "pakistan": "Pakistan", "united kingdom": "UK", "uk": "UK", "england": "UK",
    "germany": "Germany", "france": "France", "mexico": "Mexico",
    "australia": "Australia", "israel": "Israel", "uae": "UAE",
    "united arab emirates": "UAE", "netherlands": "Netherlands",
    "sweden": "Sweden", "japan": "Japan", "china": "China",
    "south korea": "South Korea", "korea": "South Korea", "brazil": "Brazil",
    "italy": "Italy", "spain": "Spain", "switzerland": "Switzerland",
    "poland": "Poland", "turkey": "Turkiye", "turkiye": "Turkiye",
    "nigeria": "Nigeria", "kenya": "Kenya", "ireland": "Ireland",
    "belgium": "Belgium", "austria": "Austria", "portugal": "Portugal",
    "denmark": "Denmark", "norway": "Norway", "finland": "Finland",
    "indonesia": "Indonesia", "malaysia": "Malaysia", "philippines": "Philippines",
    "vietnam": "Vietnam", "thailand": "Thailand", "sri lanka": "Sri Lanka",
    "bangladesh": "Bangladesh", "nepal": "Nepal", "saudi arabia": "Saudi Arabia",
    "qatar": "Qatar", "taiwan": "Taiwan", "hong kong": "Hong Kong",
    "new zealand": "New Zealand", "south africa": "South Africa",
    "argentina": "Argentina", "malta": "Malta", "luxembourg": "Luxembourg",
}
_HAS_REGION = {"USA", "Canada", "Australia"}


def geo(location):
    """Free-text location -> (country, region). '' country means 'no country known'."""
    m = (location or "").strip()
    low = m.lower()
    if not m or low in ("online", "offline", "hybrid"):
        return ("", "")
    if "online" in low and "," not in low:
        return ("", "")
    parts = [p.strip() for p in m.split(",") if p.strip()]
    country = None
    for p in reversed(parts):
        if p.lower() in _COUNTRIES:
            country = _COUNTRIES[p.lower()]
            break
    if country is None:
        return ("", "")
    region = parts[-2] if (country in _HAS_REGION and len(parts) >= 2) else ""
    return (country, region)


def get_json(url, tries=3):
    for i in range(tries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            r.raise_for_status()
            return r.json()
        except Exception as e:  # noqa: BLE001
            if i == tries - 1:
                print(f"  ! failed {url}: {e}")
                return None
            time.sleep(2 * (i + 1))


def themes_for(head, desc=""):
    """head = title + category; desc = long description (only used for Psychology)."""
    h, d = head.lower(), desc.lower()
    found = [name for name, rx in THEME_RX.items() if rx.search(h)]
    if "Psychology" not in found:
        hits = {m.group(0) for m in THEME_RX["Psychology"].finditer(d)}
        if len(hits) >= config.PSYCH_DESC_MIN_HITS:
            found.append("Psychology")
    return found


def rank_organiser(org):
    """Return (display_name, score). display_name is just the raw organiser; score used for sorting only."""
    o = org.lower()
    for rx, _, score in PRESTIGE_RX:
        if rx.search(o):
            return org, score
    if CORP_RX.search(o) and not NOT_CORP_RX.search(o):
        return org, config.CORPORATE_SCORE
    if COLLEGE_RX.search(o):
        return org, config.DEFAULT_COLLEGE_SCORE
    return org, config.DEFAULT_ORG_SCORE


# ---------------------------------------------------------------- sources
def fetch_unstop():
    out = []
    for kind in ("competitions", "hackathons"):
        page = 1
        while True:
            url = ("https://unstop.com/api/public/opportunity/search-result"
                   f"?opportunity={kind}&per_page=100&oppstatus=open&page={page}")
            data = get_json(url)
            if not data:
                break
            d = data["data"]
            for x in d["data"]:
                out.append(x)
            print(f"  unstop {kind}: page {page}/{d['last_page']}")
            if page >= d["last_page"]:
                break
            page += 1
            time.sleep(0.5)

    rows = []
    for x in out:
        org = (x.get("organisation") or {}).get("name", "")
        regn = x.get("regnRequirements") or {}
        final = parse_dt(x.get("end_date"))
        reg_deadline = parse_dt(regn.get("end_regn_dt")) or final
        prizes = x.get("prizes") or []
        cash = sum((p.get("cash") or 0) for p in prizes if isinstance(p, dict))
        category = " ".join(w.get("name", "") for w in (x.get("workfunction") or []))
        head = " ".join([x.get("title", ""), (x.get("subtype") or "").replace("_", " "), category])
        th = themes_for(head, strip_html(x.get("details"))[:6000])
        if x.get("type") == "hackathons" and "Hackathon" not in th:
            th.append("Hackathon")
        if x.get("subtype") == "case_competition" and "Case / Business" not in th:
            th.insert(0, "Case / Business")
        addr = x.get("address_with_country_logo") or {}
        country = ((addr.get("country") or {}).get("name") or "").strip()
        region = (addr.get("state") or "").strip()
        if not country:  # online events carry no address — Unstop is India-first
            country = config.UNSTOP_DEFAULT_COUNTRY
        rows.append({
            "id": f"unstop-{x['id']}",
            "title": x.get("title", "").strip(),
            "organiser": org,
            "themes": th,
            "reg_deadline": reg_deadline,
            "final_date": final,
            "mode": (x.get("region") or "").title(),
            "country": country,
            "region": region,
            "team": f"{regn.get('min_team_size', '?')}-{regn.get('max_team_size', '?')}",
            "prize": f"₹{cash:,.0f}" if cash else "",
            "registered": x.get("registerCount") or 0,
            "source": "Unstop",
            "url": x.get("seo_url") or f"https://unstop.com/{x.get('public_url', '')}",
        })
    return rows


MONTHS = "jan feb mar apr may jun jul aug sep oct nov dec".split()


def parse_devpost_period(s):
    """'Aug 26 - Oct 30, 2026' / 'Oct 05 - 27, 2026' / 'Dec 15, 2026 - Jan 10, 2027' -> end date."""
    try:
        start, end = [p.strip() for p in s.split(" - ")]
        year = int(re.search(r"(\d{4})\s*$", end).group(1))
        end_wo_year = re.sub(r",?\s*\d{4}$", "", end).strip()
        if re.match(r"^\d+$", end_wo_year):  # 'Oct 05 - 27, 2026'
            month = MONTHS.index(start[:3].lower()) + 1
            return date(year, month, int(end_wo_year))
        return datetime.strptime(f"{end_wo_year} {year}", "%b %d %Y").date()
    except Exception:  # noqa: BLE001
        return None


def fetch_devpost():
    rows, page = [], 1
    while True:
        data = get_json("https://devpost.com/api/hackathons?status[]=upcoming&status[]=open"
                        f"&per_page=40&page={page}")
        if not data or not data.get("hackathons"):
            break
        for h in data["hackathons"]:
            end = parse_devpost_period(h.get("submission_period_dates", ""))
            themes_txt = " ".join(t["name"] for t in h.get("themes", []))
            th = themes_for(h["title"] + " " + themes_txt)
            if "Hackathon" not in th:
                th.insert(0, "Hackathon")
            loc = (h.get("displayed_location") or {}).get("location", "")
            country, region = geo(loc)
            rows.append({
                "id": f"devpost-{h['id']}",
                "title": h["title"],
                "organiser": h.get("organization_name") or "",
                "themes": th,
                "reg_deadline": end,
                "final_date": end,
                "mode": "Online" if loc.lower() == "online" else loc,
                "country": country,
                "region": region,
                "team": "",
                "prize": strip_html(h.get("prize_amount", "")),
                "registered": h.get("registrations_count") or 0,
                "source": "Devpost",
                "url": h["url"],
            })
        total = data["meta"]["total_count"]
        print(f"  devpost: page {page} ({len(rows)}/{total})")
        if len(rows) >= total:
            break
        page += 1
        time.sleep(0.5)
    return rows


# ---------------------------------------------------------------- filter + rank
def process(rows):
    seen, keep = set(), []
    for r in rows:
        if r["id"] in seen:
            continue
        seen.add(r["id"])
        if not r["themes"]:
            continue  # not case/hackathon/psychology
        if not r["final_date"] or r["final_date"] < MIN_FINAL:
            continue  # final too soon (or unknown)
        if r["reg_deadline"] and r["reg_deadline"] < TODAY:
            continue  # registration already closed
        tier, score = rank_organiser(r["organiser"])
        if "Psychology" in r["themes"]:
            score += config.PSYCHOLOGY_BONUS
        r["tier"], r["score"] = tier, score
        keep.append(r)
    keep.sort(key=lambda r: (-r["score"], r["reg_deadline"] or date.max))
    return keep


# ---------------------------------------------------------------- excel
COLUMNS = [
    ("Score", 8), ("Title", 48), ("Organiser", 40), ("Themes", 22),
    ("Reg. Deadline", 14), ("Days to Reg.", 12), ("Final Date", 13), ("Days to Final", 13),
    ("Mode", 10), ("Team", 7), ("Prize", 14), ("Registered", 11), ("Source", 9),
    ("Link", 12), ("Status", 13), ("Notes", 30), ("ID", 18),
]
COL = {name: i + 1 for i, (name, _) in enumerate(COLUMNS)}
HEADER_FILL = PatternFill("solid", fgColor="1F3864")
RED = PatternFill("solid", fgColor="F8CBAD")
AMBER = PatternFill("solid", fgColor="FFE699")
GREEN = PatternFill("solid", fgColor="C6EFCE")


def load_user_notes():
    """Keep whatever you typed in Status / Notes across re-runs."""
    notes = {}
    if not XLSX.exists():
        return notes
    try:
        wb = load_workbook(XLSX)
    except Exception:  # noqa: BLE001
        return notes
    for ws in wb.worksheets:
        hdr = [c.value for c in ws[1]]
        if "ID" not in hdr:
            continue
        i_id, i_st, i_no = hdr.index("ID"), hdr.index("Status"), hdr.index("Notes")
        for row in ws.iter_rows(min_row=2, values_only=True):
            if row[i_id] and (row[i_st] or row[i_no]):
                notes.setdefault(row[i_id], (row[i_st], row[i_no]))
    return notes


def write_sheet(ws, rows, notes, table_name):
    ws.append([c for c, _ in COLUMNS])
    for i, (_, w) in enumerate(COLUMNS, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = HEADER_FILL
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.row_dimensions[1].height = 30

    for n, r in enumerate(rows, start=2):
        status, note = notes.get(r["id"], (None, None))
        reg, fin = get_column_letter(COL["Reg. Deadline"]), get_column_letter(COL["Final Date"])
        ws.append([
            r["score"], r["title"], r["organiser"], ", ".join(r["themes"]),
            r["reg_deadline"], f"={reg}{n}-TODAY()", r["final_date"], f"={fin}{n}-TODAY()",
            r["mode"], r["team"], r["prize"], r["registered"], r["source"],
            "Open", status or "", note or "", r["id"],
        ])
        link = ws.cell(n, COL["Link"])
        link.hyperlink = r["url"]
        link.font = Font(color="0563C1", underline="single")
        for k in ("Reg. Deadline", "Final Date"):
            ws.cell(n, COL[k]).number_format = "DD-MMM-YYYY"

    last = max(len(rows) + 1, 2)
    # live colour on "days to registration" — it recalculates every time you open the file
    d = get_column_letter(COL["Days to Reg."])
    rng = f"{d}2:{d}{last}"
    ws.conditional_formatting.add(rng, CellIsRule(operator="lessThan", formula=["0"],
                                                  fill=PatternFill("solid", fgColor="D9D9D9")))
    ws.conditional_formatting.add(rng, CellIsRule(operator="between", formula=["0", "3"], fill=RED))
    ws.conditional_formatting.add(rng, CellIsRule(operator="between", formula=["4", "7"], fill=AMBER))
    ws.conditional_formatting.add(rng, CellIsRule(operator="greaterThan", formula=["7"], fill=GREEN))
    s = get_column_letter(COL["Status"])
    ws.conditional_formatting.add(f"A2:{get_column_letter(len(COLUMNS))}{last}",
                                  FormulaRule(formula=[f'${s}2="Applied"'],
                                              font=Font(bold=True, color="375623")))

    from openpyxl.worksheet.datavalidation import DataValidation
    dv = DataValidation(type="list", formula1='"Interested,Applied,Registered,Skip,Done"',
                        allow_blank=True)
    ws.add_data_validation(dv)
    dv.add(f"{s}2:{s}{last}")

    if rows:
        tab = Table(displayName=table_name, ref=f"A1:{get_column_letter(len(COLUMNS))}{last}")
        tab.tableStyleInfo = TableStyleInfo(name="TableStyleLight9", showRowStripes=True)
        ws.add_table(tab)
    ws.freeze_panes = "D2"


def write_excel(rows):
    notes = load_user_notes()
    wb = Workbook()
    top = [r for r in rows if r["score"] >= config.TOP_PICK_SCORE]
    sheets = [
        ("Top Picks", top, "TopPicks"),
        ("Case Comps", [r for r in rows if "Case / Business" in r["themes"]], "CaseComps"),
        ("Hackathons", [r for r in rows if "Hackathon" in r["themes"]], "Hackathons"),
        ("Psychology", [r for r in rows if "Psychology" in r["themes"]], "Psychology"),
        ("All", rows, "AllComps"),
    ]
    for i, (name, data, tname) in enumerate(sheets):
        ws = wb.active if i == 0 else wb.create_sheet()
        ws.title = name
        write_sheet(ws, data, notes, tname)

    info = wb.create_sheet("About")
    for line in [
        ["Last updated", datetime.now().strftime("%d %b %Y %H:%M")],
        ["Rule", f"Final round on/after {MIN_FINAL:%d %b %Y} (>= {config.MIN_DAYS_TO_FINAL} days away), registration still open"],
        ["Ranking", "Score = organiser prestige (config.py) + psychology bonus. Top Picks = score >= "
                    f"{config.TOP_PICK_SCORE}"],
        ["Colours", "Days to Reg.: red 0-3, amber 4-7, green 8+ (recalculates when you open the file)"],
        ["Status/Notes", "Type anything there — it's kept when the scraper re-runs"],
        ["Sources", "Unstop (India), Devpost (global hackathons)"],
    ]:
        info.append(line)
    info.column_dimensions["A"].width = 16
    info.column_dimensions["B"].width = 110
    for c in info["A"]:
        c.font = Font(bold=True)

    target = XLSX
    try:
        wb.save(target)
    except PermissionError:
        target = HERE / f"competitions_{datetime.now():%Y%m%d_%H%M}.xlsx"
        wb.save(target)
        print(f"  ! competitions.xlsx is open in Excel — saved to {target.name} instead")
    return target, len(top)


# ---------------------------------------------------------------- calendar (.ics)
def ics_escape(s):
    return s.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def write_ics(rows):
    """One all-day event per registration deadline (with pop-up reminders) + one per final."""
    stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//stratgen//comp-finder//EN",
             "CALSCALE:GREGORIAN", "X-WR-CALNAME:Competitions"]
    for r in rows:
        for kind, d in (("REG", r["reg_deadline"]), ("FINAL", r["final_date"])):
            if not d or (kind == "FINAL" and d == r["reg_deadline"]):
                continue
            label = "Reg. deadline" if kind == "REG" else "Final"
            summary = ics_escape(f"[{label}] {r['title']}")
            desc = ics_escape(f"{r['organiser']} | {r['tier']} | {r['url']}")
            lines += [
                "BEGIN:VEVENT",
                f"UID:{r['id']}-{kind.lower()}@stratgen",
                f"DTSTAMP:{stamp}",
                f"DTSTART;VALUE=DATE:{d:%Y%m%d}",
                f"DTEND;VALUE=DATE:{d + timedelta(days=1):%Y%m%d}",
                f"SUMMARY:{summary}",
                f"DESCRIPTION:{desc}",
                f"URL:{r['url']}",
            ]
            if kind == "REG":
                for days in config.REMINDER_DAYS_BEFORE:
                    lines += ["BEGIN:VALARM", "ACTION:DISPLAY",
                              f"DESCRIPTION:{ics_escape(r['title'])} registration closes in {days} day(s)",
                              f"TRIGGER:-P{days}D", "END:VALARM"]
            lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    ICS.write_text("\r\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------- main
def main():
    print(f"Finding competitions (final on/after {MIN_FINAL:%d %b %Y})...")
    rows = []
    for name, fn in (("Unstop", fetch_unstop), ("Devpost", fetch_devpost)):
        try:
            rows += fn()
        except Exception as e:  # noqa: BLE001 — one source failing shouldn't kill the run
            print(f"  ! {name} failed: {e}")
    print(f"Fetched {len(rows)} listings")

    kept = process(rows)
    path, n_top = write_excel(kept)
    top = [r for r in kept if r["score"] >= config.TOP_PICK_SCORE]
    write_ics(top)

    snap = [{**r, "reg_deadline": str(r["reg_deadline"]), "final_date": str(r["final_date"])}
            for r in kept]
    SNAPSHOT.write_text(json.dumps(snap, indent=1, ensure_ascii=False), encoding="utf-8")

    by = {t: sum(t in r["themes"] for r in kept) for t in config.THEMES}
    print(f"\nKept {len(kept)} ({', '.join(f'{k}: {v}' for k, v in by.items())}); "
          f"top picks: {n_top}")
    print(f"Excel:    {path}")
    print(f"Calendar: {ICS}  (top picks only — import into Google/Outlook calendar)")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
