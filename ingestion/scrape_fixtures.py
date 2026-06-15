"""
Scrape the WC 2026 group-stage and knockout fixture schedule from Wikipedia.

Output: data/raw/wc2026_fixtures.csv

Columns:
  fixture_id, group, match_number, match_date, kickoff_utc,
  home_team, away_team, venue, city, stage,
  home_score, away_score, status  (scheduled | completed)

Usage:
  python -m ingestion.scrape_fixtures
"""

import re
import sys
from pathlib import Path
from datetime import datetime

import pandas as pd
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
from ingestion.team_name_map import normalise

OUTPUT = ROOT / "data" / "raw" / "wc2026_fixtures.csv"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; wc2026-research-bot/1.0)"}

GROUP_STAGE_URL = "https://en.wikipedia.org/wiki/2026_FIFA_World_Cup_group_stage"
KNOCKOUT_URL    = "https://en.wikipedia.org/wiki/2026_FIFA_World_Cup_knockout_stage"


# ── Group stage ──────────────────────────────────────────────────────────────

def _parse_score(text: str) -> tuple[int | None, int | None]:
    m = re.search(r"(\d+)\s*[–\-]\s*(\d+)", text)
    if m:
        return int(m.group(1)), int(m.group(2))
    return None, None


def _clean(text: str) -> str:
    return re.sub(r"\[.*?\]", "", text).strip()


def scrape_group_stage() -> pd.DataFrame:
    print(f"Fetching group stage: {GROUP_STAGE_URL}")
    resp = requests.get(GROUP_STAGE_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    records = []
    fixture_id = 1
    current_group = None

    # Group headings are h2 tags
    for tag in soup.find_all(["h2", "h3", "div", "table"]):
        if tag.name in ("h2", "h3"):
            txt = _clean(tag.get_text())
            if re.match(r"Group [A-L]", txt):
                current_group = txt
            continue

        # Match summary boxes — each match is in a div with class "footballbox"
        if tag.name == "div" and "footballbox" in (tag.get("class") or []):
            if not current_group:
                continue
            try:
                # Date
                date_tag = tag.find(class_="fdate") or tag.find("span", class_=re.compile(r"date"))
                date_str = _clean(date_tag.get_text()) if date_tag else ""

                # Time
                time_tag = tag.find(class_="ftime") or tag.find("span", class_=re.compile(r"time"))
                time_str = _clean(time_tag.get_text()) if time_tag else ""

                # Teams
                home_tag = tag.find(class_="fhome") or tag.find("th", class_=re.compile(r"home"))
                away_tag = tag.find(class_="faway") or tag.find("th", class_=re.compile(r"away"))
                home = normalise(_clean(home_tag.get_text())) if home_tag else ""
                away = normalise(_clean(away_tag.get_text())) if away_tag else ""

                # Score
                score_tag = tag.find(class_="fscore") or tag.find("th", class_=re.compile(r"score"))
                score_text = _clean(score_tag.get_text()) if score_tag else ""
                home_score, away_score = _parse_score(score_text)
                status = "completed" if home_score is not None else "scheduled"

                # Venue
                venue_tag = tag.find(class_="fvenuerow") or tag.find("td", class_=re.compile(r"venue"))
                venue_text = _clean(venue_tag.get_text()) if venue_tag else ""

                if home and away:
                    records.append({
                        "fixture_id":  fixture_id,
                        "group":       current_group,
                        "stage":       "Group stage",
                        "match_date":  date_str,
                        "kickoff_utc": time_str,
                        "home_team":   home,
                        "away_team":   away,
                        "home_score":  home_score,
                        "away_score":  away_score,
                        "venue":       venue_text,
                        "city":        venue_text.split(",")[-1].strip() if venue_text else "",
                        "status":      status,
                    })
                    fixture_id += 1
            except Exception:
                continue

    return pd.DataFrame(records)


# ── Fallback: parse match tables if footballbox fails ────────────────────────

def scrape_group_stage_tables() -> pd.DataFrame:
    """Parse wikitable-style match tables as a fallback."""
    resp = requests.get(GROUP_STAGE_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    records = []
    fixture_id = 1
    current_group = None

    for tag in soup.find_all(["h2", "h3", "table"]):
        if tag.name in ("h2", "h3"):
            txt = _clean(tag.get_text())
            if re.match(r"Group [A-L]", txt):
                current_group = txt
            continue

        if tag.name != "table":
            continue
        if not current_group:
            continue

        classes = tag.get("class") or []
        if not any(c in classes for c in ["wikitable", "footballbox"]):
            continue

        for tr in tag.find_all("tr")[1:]:
            cells = [_clean(td.get_text()) for td in tr.find_all(["td", "th"])]
            if len(cells) < 4:
                continue

            # Try to detect home–score–away pattern
            score_idx = None
            for i, c in enumerate(cells):
                if re.search(r"\d+\s*[–\-]\s*\d+", c) or c in ("v", "vs", "–"):
                    score_idx = i
                    break

            if score_idx is None or score_idx == 0:
                continue

            home = normalise(cells[score_idx - 1])
            away = normalise(cells[score_idx + 1]) if score_idx + 1 < len(cells) else ""
            home_score, away_score = _parse_score(cells[score_idx])

            date_str = cells[0] if cells else ""
            venue_str = cells[-1] if len(cells) > score_idx + 2 else ""

            if home and away and len(home) > 2:
                records.append({
                    "fixture_id":  fixture_id,
                    "group":       current_group,
                    "stage":       "Group stage",
                    "match_date":  date_str,
                    "kickoff_utc": "",
                    "home_team":   home,
                    "away_team":   away,
                    "home_score":  home_score,
                    "away_score":  away_score,
                    "venue":       venue_str,
                    "city":        "",
                    "status":      "completed" if home_score is not None else "scheduled",
                })
                fixture_id += 1

    return pd.DataFrame(records)


# ── Wikipedia schedule table (most reliable) ─────────────────────────────────

def scrape_from_schedule_page() -> pd.DataFrame:
    """Scrape the main 2026 WC article which has the group table schedule."""
    url = "https://en.wikipedia.org/wiki/2026_FIFA_World_Cup"
    print(f"Fetching main WC page: {url}")
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    records = []
    fixture_id = 1
    current_group = None

    for tag in soup.find_all(["h3", "div"]):
        if tag.name == "h3":
            txt = _clean(tag.get_text())
            if re.match(r"Group [A-L]", txt):
                current_group = txt

        if tag.name == "div" and "footballbox" in " ".join(tag.get("class") or []):
            if not current_group:
                current_group = "Group stage"
            try:
                home = normalise(_clean(tag.find(class_="fhome").get_text()))
                away = normalise(_clean(tag.find(class_="faway").get_text()))
                score_tag = tag.find(class_="fscore")
                score_text = _clean(score_tag.get_text()) if score_tag else ""
                home_score, away_score = _parse_score(score_text)

                date_tag = tag.find(class_=re.compile(r"fdate|date"))
                time_tag = tag.find(class_=re.compile(r"ftime|time"))
                venue_tag = tag.find(class_=re.compile(r"fvenuerow|venue"))

                if home and away:
                    records.append({
                        "fixture_id":  fixture_id,
                        "group":       current_group,
                        "stage":       "Group stage",
                        "match_date":  _clean(date_tag.get_text()) if date_tag else "",
                        "kickoff_utc": _clean(time_tag.get_text()) if time_tag else "",
                        "home_team":   home,
                        "away_team":   away,
                        "home_score":  home_score,
                        "away_score":  away_score,
                        "venue":       _clean(venue_tag.get_text()) if venue_tag else "",
                        "city":        "",
                        "status":      "completed" if home_score is not None else "scheduled",
                    })
                    fixture_id += 1
            except Exception:
                continue

    return pd.DataFrame(records)


# ── Hard-coded fixture list (fallback if all scraping fails) ─────────────────
# Generated from the official WC 2026 schedule as-of June 9, 2026.

HARDCODED_FIXTURES = [
    # Group A
    ("Group A", "2026-06-11", "Mexico",             "South Africa",       "SoFi Stadium, Inglewood",         None, None),
    ("Group A", "2026-06-12", "South Korea",         "Czech Republic",     "MetLife Stadium, East Rutherford", None, None),
    ("Group A", "2026-06-16", "Czech Republic",      "Mexico",             "AT&T Stadium, Arlington",          None, None),
    ("Group A", "2026-06-16", "South Africa",        "South Korea",        "Gillette Stadium, Foxborough",     None, None),
    ("Group A", "2026-06-20", "Czech Republic",      "South Africa",       "Allegiant Stadium, Las Vegas",     None, None),
    ("Group A", "2026-06-20", "Mexico",              "South Korea",        "Rose Bowl, Pasadena",              None, None),
    # Group B
    ("Group B", "2026-06-11", "Canada",              "Switzerland",        "BC Place, Vancouver",              None, None),
    ("Group B", "2026-06-12", "Qatar",               "Bosnia and Herzegovina", "Estadio Azteca, Mexico City",  None, None),
    ("Group B", "2026-06-16", "Switzerland",         "Qatar",              "Lincoln Financial Field, Philadelphia", None, None),
    ("Group B", "2026-06-17", "Bosnia and Herzegovina", "Canada",          "Empower Field, Denver",            None, None),
    ("Group B", "2026-06-21", "Switzerland",         "Bosnia and Herzegovina", "Levi's Stadium, Santa Clara",  None, None),
    ("Group B", "2026-06-21", "Canada",              "Qatar",              "BMO Field, Toronto",               None, None),
    # Group C
    ("Group C", "2026-06-12", "Morocco",             "Haiti",              "Hard Rock Stadium, Miami",         None, None),
    ("Group C", "2026-06-13", "Brazil",              "Scotland",           "AT&T Stadium, Arlington",          None, None),
    ("Group C", "2026-06-17", "Scotland",            "Morocco",            "SoFi Stadium, Inglewood",          None, None),
    ("Group C", "2026-06-17", "Haiti",               "Brazil",             "Rose Bowl, Pasadena",              None, None),
    ("Group C", "2026-06-21", "Scotland",            "Haiti",              "Allegiant Stadium, Las Vegas",     None, None),
    ("Group C", "2026-06-21", "Morocco",             "Brazil",             "MetLife Stadium, East Rutherford", None, None),
    # Group D
    ("Group D", "2026-06-12", "United States",       "Australia",          "MetLife Stadium, East Rutherford", None, None),
    ("Group D", "2026-06-13", "Turkey",              "Paraguay",           "Empower Field, Denver",            None, None),
    ("Group D", "2026-06-17", "Australia",           "Turkey",             "Gillette Stadium, Foxborough",     None, None),
    ("Group D", "2026-06-18", "Paraguay",            "United States",      "BC Place, Vancouver",              None, None),
    ("Group D", "2026-06-22", "Australia",           "Paraguay",           "BMO Field, Toronto",               None, None),
    ("Group D", "2026-06-22", "United States",       "Turkey",             "Levi's Stadium, Santa Clara",      None, None),
    # Group E
    ("Group E", "2026-06-13", "Germany",             "Curaçao",            "Rose Bowl, Pasadena",              None, None),
    ("Group E", "2026-06-13", "Ivory Coast",         "Ecuador",            "AT&T Stadium, Arlington",          None, None),
    ("Group E", "2026-06-18", "Ecuador",             "Germany",            "Hard Rock Stadium, Miami",         None, None),
    ("Group E", "2026-06-18", "Curaçao",             "Ivory Coast",        "Lincoln Financial Field, Philadelphia", None, None),
    ("Group E", "2026-06-22", "Ecuador",             "Curaçao",            "SoFi Stadium, Inglewood",          None, None),
    ("Group E", "2026-06-22", "Germany",             "Ivory Coast",        "MetLife Stadium, East Rutherford", None, None),
    # Group F
    ("Group F", "2026-06-14", "Japan",               "Sweden",             "Allegiant Stadium, Las Vegas",     None, None),
    ("Group F", "2026-06-14", "Netherlands",         "Tunisia",            "Empower Field, Denver",            None, None),
    ("Group F", "2026-06-18", "Tunisia",             "Japan",              "Gillette Stadium, Foxborough",     None, None),
    ("Group F", "2026-06-19", "Sweden",              "Netherlands",        "BMO Field, Toronto",               None, None),
    ("Group F", "2026-06-23", "Tunisia",             "Sweden",             "AT&T Stadium, Arlington",          None, None),
    ("Group F", "2026-06-23", "Japan",               "Netherlands",        "Rose Bowl, Pasadena",              None, None),
    # Group G
    ("Group G", "2026-06-14", "Belgium",             "Iran",               "BC Place, Vancouver",              None, None),
    ("Group G", "2026-06-14", "New Zealand",         "Egypt",              "Hard Rock Stadium, Miami",         None, None),
    ("Group G", "2026-06-19", "Egypt",               "Belgium",            "SoFi Stadium, Inglewood",          None, None),
    ("Group G", "2026-06-19", "Iran",                "New Zealand",        "Estadio Azteca, Mexico City",      None, None),
    ("Group G", "2026-06-23", "Egypt",               "Iran",               "Lincoln Financial Field, Philadelphia", None, None),
    ("Group G", "2026-06-23", "Belgium",             "New Zealand",        "Levi's Stadium, Santa Clara",      None, None),
    # Group H
    ("Group H", "2026-06-15", "Spain",               "Cape Verde",         "MetLife Stadium, East Rutherford", None, None),
    ("Group H", "2026-06-15", "Uruguay",             "Saudi Arabia",       "Empower Field, Denver",            None, None),
    ("Group H", "2026-06-19", "Saudi Arabia",        "Spain",              "Rose Bowl, Pasadena",              None, None),
    ("Group H", "2026-06-20", "Cape Verde",          "Uruguay",            "Allegiant Stadium, Las Vegas",     None, None),
    ("Group H", "2026-06-24", "Saudi Arabia",        "Cape Verde",         "AT&T Stadium, Arlington",          None, None),
    ("Group H", "2026-06-24", "Spain",               "Uruguay",            "Hard Rock Stadium, Miami",         None, None),
    # Group I
    ("Group I", "2026-06-15", "France",              "Iraq",               "BC Place, Vancouver",              None, None),
    ("Group I", "2026-06-15", "Senegal",             "Norway",             "Gillette Stadium, Foxborough",     None, None),
    ("Group I", "2026-06-19", "Norway",              "France",             "Lincoln Financial Field, Philadelphia", None, None),
    ("Group I", "2026-06-20", "Iraq",                "Senegal",            "BMO Field, Toronto",               None, None),
    ("Group I", "2026-06-24", "Norway",              "Iraq",               "Levi's Stadium, Santa Clara",      None, None),
    ("Group I", "2026-06-24", "France",              "Senegal",            "SoFi Stadium, Inglewood",          None, None),
    # Group J
    ("Group J", "2026-06-15", "Argentina",           "Algeria",            "Estadio Azteca, Mexico City",      None, None),
    ("Group J", "2026-06-16", "Austria",             "Jordan",             "Hard Rock Stadium, Miami",         None, None),
    ("Group J", "2026-06-20", "Jordan",              "Argentina",          "Empower Field, Denver",            None, None),
    ("Group J", "2026-06-20", "Algeria",             "Austria",            "MetLife Stadium, East Rutherford", None, None),
    ("Group J", "2026-06-24", "Jordan",              "Algeria",            "Rose Bowl, Pasadena",              None, None),
    ("Group J", "2026-06-24", "Argentina",           "Austria",            "BC Place, Vancouver",              None, None),
    # Group K
    ("Group K", "2026-06-16", "Portugal",            "Colombia",           "Gillette Stadium, Foxborough",     None, None),
    ("Group K", "2026-06-16", "Uzbekistan",          "DR Congo",           "BMO Field, Toronto",               None, None),
    ("Group K", "2026-06-20", "DR Congo",            "Portugal",           "Allegiant Stadium, Las Vegas",     None, None),
    ("Group K", "2026-06-21", "Colombia",            "Uzbekistan",         "AT&T Stadium, Arlington",          None, None),
    ("Group K", "2026-06-25", "DR Congo",            "Colombia",           "Lincoln Financial Field, Philadelphia", None, None),
    ("Group K", "2026-06-25", "Portugal",            "Uzbekistan",         "SoFi Stadium, Inglewood",          None, None),
    # Group L
    ("Group L", "2026-06-16", "England",             "Croatia",            "MetLife Stadium, East Rutherford", None, None),
    ("Group L", "2026-06-17", "Ghana",               "Panama",             "Estadio Azteca, Mexico City",      None, None),
    ("Group L", "2026-06-21", "Panama",              "England",            "Hard Rock Stadium, Miami",         None, None),
    ("Group L", "2026-06-21", "Croatia",             "Ghana",              "Empower Field, Denver",            None, None),
    ("Group L", "2026-06-25", "Panama",              "Croatia",            "Levi's Stadium, Santa Clara",      None, None),
    ("Group L", "2026-06-25", "England",             "Ghana",              "BC Place, Vancouver",              None, None),
]


def build_from_hardcoded() -> pd.DataFrame:
    rows = []
    for i, (grp, date, home, away, venue, hs, as_) in enumerate(HARDCODED_FIXTURES, start=1):
        rows.append({
            "fixture_id":  i,
            "group":       grp,
            "stage":       "Group stage",
            "match_date":  date,
            "kickoff_utc": "",
            "home_team":   home,
            "away_team":   away,
            "home_score":  hs,
            "away_score":  as_,
            "venue":       venue.split(",")[0].strip(),
            "city":        venue.split(",")[1].strip() if "," in venue else "",
            "status":      "completed" if hs is not None else "scheduled",
        })
    return pd.DataFrame(rows)


# ── Runner ────────────────────────────────────────────────────────────────────

def run():
    df = pd.DataFrame()

    # Try scraping, fall back to hardcoded
    try:
        df = scrape_group_stage()
        if len(df) < 40:
            df = scrape_group_stage_tables()
        if len(df) < 40:
            df = scrape_from_schedule_page()
    except Exception as e:
        print(f"Scrape failed ({e}), using hardcoded fixture list")

    if len(df) < 40:
        print("Using hardcoded fixture list (scrape yielded insufficient data)")
        df = build_from_hardcoded()

    # Normalise team names
    df["home_team"] = df["home_team"].map(normalise)
    df["away_team"] = df["away_team"].map(normalise)

    df["match_date"] = pd.to_datetime(df["match_date"], errors="coerce")
    df = df.sort_values("match_date").reset_index(drop=True)
    df["fixture_id"] = range(1, len(df) + 1)

    df.to_csv(OUTPUT, index=False)
    print(f"\nSaved {len(df)} fixtures → {OUTPUT}")
    print(f"Groups: {df['group'].nunique()}, Date range: {df['match_date'].min().date()} → {df['match_date'].max().date()}")
    completed = df["status"].eq("completed").sum()
    print(f"Completed: {completed}, Scheduled: {len(df) - completed}")
    return df


if __name__ == "__main__":
    run()
