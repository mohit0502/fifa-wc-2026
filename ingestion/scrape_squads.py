"""
Scrape 2026 WC squads from Wikipedia.

For each of the 48 qualified nations scrapes:
  player name, position, shirt number, date of birth, age,
  caps, international goals, club, club country

Output: data/raw/wc2026_squads.csv

Usage:
  python -m ingestion.scrape_squads
"""

import re
import sys
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
from ingestion.team_name_map import normalise

OUTPUT = ROOT / "data" / "raw" / "wc2026_squads.csv"

WIKI_URL = "https://en.wikipedia.org/wiki/2026_FIFA_World_Cup_squads"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; wc2026-research-bot/1.0)"}

POS_MAP = {
    "GK": "GK", "Goalkeeper": "GK", "1 GK": "GK",
    "DF": "DEF", "Defender": "DEF", "CB": "DEF", "LB": "DEF", "RB": "DEF", "2 DF": "DEF",
    "MF": "MID", "Midfielder": "MID", "CM": "MID", "DM": "MID", "AM": "MID", "3 MF": "MID",
    "FW": "FWD", "Forward": "FWD", "CF": "FWD", "LW": "FWD", "RW": "FWD", "4 FW": "FWD",
    "ST": "FWD",
}


def _clean_text(cell) -> str:
    return cell.get_text(separator=" ", strip=True)


def _parse_age(text: str) -> int | None:
    m = re.search(r"aged?\s*(\d+)", text, re.I) or re.search(r"\((\d+)\)", text)
    return int(m.group(1)) if m else None


def _parse_dob(text: str) -> str | None:
    """Extract YYYY-MM-DD from strings like '(1995-03-15)' or '15 March 1995'."""
    iso = re.search(r"(\d{4}-\d{2}-\d{2})", text)
    if iso:
        return iso.group(1)
    long = re.search(
        r"(\d{1,2})\s+(January|February|March|April|May|June|July|August|"
        r"September|October|November|December)\s+(\d{4})", text, re.I
    )
    if long:
        months = {
            "january": "01", "february": "02", "march": "03", "april": "04",
            "may": "05", "june": "06", "july": "07", "august": "08",
            "september": "09", "october": "10", "november": "11", "december": "12",
        }
        d, m_str, y = long.group(1), long.group(2).lower(), long.group(3)
        return f"{y}-{months[m_str]}-{int(d):02d}"
    return None


def _parse_int(text: str) -> int | None:
    m = re.search(r"(\d+)", text.replace(",", ""))
    return int(m.group(1)) if m else None


def _extract_club_country(cell) -> tuple[str | None, str | None]:
    """Return (club_name, club_country) from a club cell with flag img."""
    club = cell.get_text(strip=True)
    flag_img = cell.find("img")
    country = None
    if flag_img:
        alt = flag_img.get("alt", "")
        country = alt.strip() if alt else None
    return club or None, country


def scrape_squads() -> pd.DataFrame:
    print(f"Fetching {WIKI_URL}")
    resp = requests.get(WIKI_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    records = []
    current_team = None
    current_group = None

    # Walk through all headings and tables in document order
    for tag in soup.find_all(["h2", "h3", "table"]):
        if tag.name == "h2":
            txt = tag.get_text(strip=True).replace("[edit]", "").strip()
            if txt.startswith("Group"):
                current_group = txt
        elif tag.name == "h3":
            txt = tag.get_text(strip=True).replace("[edit]", "").strip()
            # Each h3 is a team name
            if current_group:
                current_team = normalise(txt)
        elif tag.name == "table" and current_team:
            if "wikitable" not in (tag.get("class") or []):
                continue

            headers_row = tag.find("tr")
            if not headers_row:
                continue
            col_names = [th.get_text(strip=True).lower() for th in headers_row.find_all(["th", "td"])]

            # Map column indices
            idx = {}
            for i, h in enumerate(col_names):
                if h in ("no.", "no", "#"):
                    idx.setdefault("number", i)
                elif h in ("pos.", "pos", "position"):
                    idx.setdefault("position", i)
                elif "player" in h or "name" in h:
                    idx.setdefault("player", i)
                elif "birth" in h or "dob" in h or "age" in h:
                    idx.setdefault("dob", i)
                elif "cap" in h:
                    idx.setdefault("caps", i)
                elif "goal" in h:
                    idx.setdefault("goals", i)
                elif "club" in h:
                    idx.setdefault("club", i)

            if "player" not in idx:
                continue

            for tr in tag.find_all("tr")[1:]:
                cells = tr.find_all(["td", "th"])
                if len(cells) < 3:
                    continue
                try:
                    def cell_text(key):
                        i = idx.get(key)
                        return _clean_text(cells[i]) if i is not None and i < len(cells) else ""

                    number    = _parse_int(cell_text("number"))
                    raw_pos   = cell_text("position")
                    position  = POS_MAP.get(raw_pos.upper(), raw_pos) if raw_pos else None
                    player    = cell_text("player")
                    dob_raw   = cell_text("dob")
                    dob       = _parse_dob(dob_raw)
                    age       = _parse_age(dob_raw)
                    caps      = _parse_int(cell_text("caps"))
                    goals     = _parse_int(cell_text("goals"))

                    club_idx = idx.get("club")
                    if club_idx is not None and club_idx < len(cells):
                        club, club_country = _extract_club_country(cells[club_idx])
                    else:
                        club, club_country = None, None

                    # Skip header repeat rows
                    if not player or player.lower() in ("player", "name", ""):
                        continue

                    records.append({
                        "team_name":        current_team,
                        "group":            current_group,
                        "squad_number":     number,
                        "position":         position,
                        "player_name":      player,
                        "date_of_birth":    dob,
                        "age":              age,
                        "caps":             caps,
                        "international_goals": goals,
                        "club":             club,
                        "club_country":     club_country,
                        "is_wc2026":        True,
                        "data_source":      "wikipedia_2026",
                    })
                except (IndexError, ValueError):
                    continue

    df = pd.DataFrame(records)
    if df.empty:
        print("WARNING: no data scraped")
        return df

    df["team_name"] = df["team_name"].map(normalise)
    df = df[df["player_name"].str.len() > 1]
    df = df.drop_duplicates(subset=["team_name", "player_name"])

    print(f"Scraped {len(df)} players across {df['team_name'].nunique()} teams")
    df.to_csv(OUTPUT, index=False)
    print(f"Saved → {OUTPUT}")
    return df


if __name__ == "__main__":
    scrape_squads()
