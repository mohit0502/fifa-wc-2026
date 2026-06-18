"""
Rebuild data/raw/wc2026_fixtures.csv from the 12 official Wikipedia
"2026 FIFA World Cup Group X" pages, parsing the structured
{{#invoke:football box|main ...}} match templates directly.

This replaces the old scrape_fixtures.py approach (HTML "footballbox"
divs on a dedicated group-stage article that no longer exists / never
existed at that URL) which produced an incorrect schedule — verified by
cross-checking Group I, where the real matchday-1 fixtures (France vs
Senegal, Norway vs Iraq) didn't match what was stored locally.

Usage:
    python -m ingestion.scrape_official_schedule
"""

import re
import sys
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from ingestion.team_name_map import normalise

OUTPUT = ROOT / "data" / "raw" / "wc2026_fixtures.csv"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; wc2026-research-bot/1.0)"}
API_URL = "https://en.wikipedia.org/w/api.php"

GROUP_LETTERS = list("ABCDEFGHIJKL")

SECTION_RE = re.compile(r'<section begin="?(\w+)"? />(.*?)<section end="?\1"? />', re.S)
DATE_RE    = re.compile(r"date=\{\{Start date\|(\d+)\|(\d+)\|(\d+)\}\}")
TEAM1_RE   = re.compile(r"team1=\{\{#invoke:flag\|fb-rt\|(\w+)\}\}")
TEAM2_RE   = re.compile(r"team2=\{\{#invoke:flag\|fb\|(\w+)\}\}")
SCORE_RE   = re.compile(r"score=\{\{score link\|[^|]*\|([^}]+)\}\}")
STADIUM_RE = re.compile(r"stadium=(.*?)\n")
WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")


def _strip_links(text: str) -> str:
    return WIKILINK_RE.sub(lambda m: m.group(1), text).strip()


def fetch_group_wikitext(letter: str, retries: int = 4) -> str:
    for attempt in range(retries):
        resp = requests.get(API_URL, params={
            "action": "parse",
            "page": f"2026_FIFA_World_Cup_Group_{letter}",
            "prop": "wikitext",
            "format": "json",
        }, headers=HEADERS, timeout=30)
        if resp.status_code == 429:
            wait = 5 * (attempt + 1)
            print(f"  rate limited, waiting {wait}s...")
            time.sleep(wait)
            continue
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            raise RuntimeError(data["error"])
        return data["parse"]["wikitext"]["*"]
    raise RuntimeError(f"Group {letter}: exceeded retries on 429")


def parse_group(letter: str) -> list[dict]:
    txt = fetch_group_wikitext(letter)
    records = []
    for section_id, block in SECTION_RE.findall(txt):
        date_m  = DATE_RE.search(block)
        t1_m    = TEAM1_RE.search(block)
        t2_m    = TEAM2_RE.search(block)
        score_m = SCORE_RE.search(block)
        stad_m  = STADIUM_RE.search(block)
        if not (date_m and t1_m and t2_m):
            print(f"  ! skipping {section_id}: incomplete template")
            continue

        year, month, day = date_m.groups()
        match_date = f"{year}-{int(month):02d}-{int(day):02d}"
        home = normalise(t1_m.group(1))
        away = normalise(t2_m.group(1))

        score_text = score_m.group(1).strip() if score_m else ""
        score_digits = re.match(r"(\d+)\s*[–\-]\s*(\d+)", score_text)
        if score_digits:
            home_score, away_score = int(score_digits.group(1)), int(score_digits.group(2))
            status = "completed"
        else:
            home_score, away_score = None, None
            status = "scheduled"

        stadium_raw = _strip_links(stad_m.group(1)) if stad_m else ""
        venue, _, city = stadium_raw.partition(", ")

        records.append({
            "group":      f"Group {letter}",
            "stage":      "Group stage",
            "match_date": match_date,
            "kickoff_utc": "",
            "home_team":  home,
            "away_team":  away,
            "home_score": home_score,
            "away_score": away_score,
            "venue":      venue,
            "city":       city,
            "status":     status,
            "_section":   section_id,
        })
    return records


def run() -> pd.DataFrame:
    all_records = []
    for letter in GROUP_LETTERS:
        print(f"Fetching Group {letter}...")
        try:
            recs = parse_group(letter)
        except Exception as e:
            print(f"  ! Group {letter} failed: {e}")
            continue
        print(f"  {len(recs)} matches  "
              f"({sum(1 for r in recs if r['status']=='completed')} completed)")
        all_records.extend(recs)
        time.sleep(2.0)  # be polite to the API

    df = pd.DataFrame(all_records)

    # Sort chronologically; within the same date, group letter then
    # section index (A1, A2, ...) keeps each group's own match order intact.
    df["match_date_dt"] = pd.to_datetime(df["match_date"])
    df["_section_num"] = df["_section"].str.extract(r"(\d+)").astype(int)
    df = df.sort_values(["match_date_dt", "group", "_section_num"]).reset_index(drop=True)
    df["fixture_id"] = range(1, len(df) + 1)
    df = df.drop(columns=["match_date_dt", "_section", "_section_num"])

    cols = ["fixture_id", "group", "stage", "match_date", "kickoff_utc",
            "home_team", "away_team", "home_score", "away_score",
            "venue", "city", "status"]
    df = df[cols]

    df.to_csv(OUTPUT, index=False)
    completed = (df["status"] == "completed").sum()
    print(f"\nSaved {len(df)} fixtures → {OUTPUT}")
    print(f"Completed: {completed}/{len(df)}")
    return df


if __name__ == "__main__":
    run()
