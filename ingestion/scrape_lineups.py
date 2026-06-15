"""
Scrape pre-tournament predicted XIs from RotoWire for all 48 WC 2026 teams.

URL: https://www.rotowire.com/soccer/lineups.php?league=WOC
Output: data/raw/lineups.json

Each team entry:
  {
    "team_name": "England",
    "status":    "predicted" | "confirmed",
    "formation": "4-2-3-1",
    "players": [
      {"pos": "GK",  "name": "Jordan Pickford", "short_name": "J. Pickford", "injury": null},
      ...
    ],
    "injuries": [
      {"pos": "F",   "name": "Marcus Rashford",  "injury": "QUES"}
    ],
    "scraped_at": "2026-06-10T..."
  }

Usage:
    python -m ingestion.scrape_lineups
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
from ingestion.team_name_map import normalise

OUTPUT = ROOT / "data" / "raw" / "lineups.json"
URL    = "https://www.rotowire.com/soccer/lineups.php?league=WOC"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# RotoWire name → canonical (for names not handled by normalise())
EXTRA_MAP = {
    "Cote D'ivoire": "Ivory Coast",
    "Ivory Coast":   "Ivory Coast",
    "USA":           "United States",
    "Curacao":       "Curaçao",
    "Bosnia and Herzegovina": "Bosnia and Herzegovina",
}

# Position → broad tier for formation calculation
def _tier(pos: str) -> str:
    p = pos.upper()
    if p == "GK":                       return "GK"
    if p.startswith("D") and "M" not in p: return "DEF"   # DL, DC, DR, D
    if p in ("DMC", "DML", "DMR", "DM"): return "DM"
    if p.startswith("AM"):              return "AM"
    if p.startswith("FW") or p in ("ST", "CF", "SS"): return "FW"
    if p.startswith("M"):               return "MID"       # ML, MC, MR, MC
    return "MID"

def _infer_formation(players: list[dict]) -> str:
    """Infer formation string from list of 11 player dicts (excluding GK)."""
    # Collapse tiers: DEF, DM (optional), MID (optional), AM (optional), FW
    tier_counts: dict[str, int] = {}
    for p in players:
        t = _tier(p["pos"])
        if t != "GK":
            tier_counts[t] = tier_counts.get(t, 0) + 1

    # Build formation in order DEF → DM → MID → AM → FW
    parts = []
    for t in ["DEF", "DM", "MID", "AM", "FW"]:
        if tier_counts.get(t, 0) > 0:
            parts.append(str(tier_counts[t]))
    return "-".join(parts) if parts else "unknown"


def _parse_player(li) -> dict:
    """Parse a single li.lineup__player element."""
    pos_div = li.find("div", class_="lineup__pos")
    pos = pos_div.get_text(strip=True) if pos_div else "?"

    link = li.find("a")
    if link:
        full_name  = link.get("title", "").strip()
        short_name = link.get_text(strip=True)
    else:
        full_name  = li.get_text(strip=True)
        short_name = full_name

    # Extract injury status suffix (QUES, OUT, SUSP, DTD…)
    injury = None
    for flag in ("OUT", "QUES", "SUSP", "DTD", "INJ"):
        if short_name.endswith(flag):
            injury = flag
            short_name = short_name[: -len(flag)].strip()
            break

    name = full_name if full_name else short_name
    return {"pos": pos, "name": name, "short_name": short_name, "injury": injury}


def _rw_to_canonical(name: str) -> str:
    """Map RotoWire team name to canonical."""
    if name in EXTRA_MAP:
        return EXTRA_MAP[name]
    return normalise(name)


def scrape() -> dict:
    print(f"Fetching {URL}")
    resp = requests.get(URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    results: dict[str, dict] = {}
    now = datetime.now(timezone.utc).isoformat()

    lineup_blocks = soup.find_all("div", class_="lineup is-soccer")
    print(f"Found {len(lineup_blocks)} lineup blocks")

    for block in lineup_blocks:
        for side in ("is-home", "is-visit"):
            mteam_div = block.find("div", class_=f"lineup__mteam {side}")
            if not mteam_div:
                continue
            raw_name  = mteam_div.get_text(strip=True)
            team_name = _rw_to_canonical(raw_name)

            # Already collected this team's lineup from an earlier fixture
            if team_name in results:
                continue

            ul = block.find("ul", class_=f"lineup__list {side}")
            if not ul:
                continue

            # Status
            status_li = ul.find("li", class_="lineup__status")
            raw_status = status_li.get_text(strip=True).lower() if status_li else ""
            status = "confirmed" if "confirmed" in raw_status else "predicted"

            # Players: collect until injuries title
            starters: list[dict] = []
            injuries: list[dict] = []
            in_injuries = False

            for li in ul.find_all("li"):
                classes = li.get("class") or []
                if "lineup__title" in classes:
                    in_injuries = True
                    continue
                if "lineup__status" in classes:
                    continue
                if "lineup__no" in classes:
                    continue
                if "lineup__player" not in classes:
                    continue

                player = _parse_player(li)
                if in_injuries:
                    injuries.append(player)
                else:
                    starters.append(player)

            # Only keep first 11 starters
            starters = starters[:11]
            if len(starters) < 11:
                print(f"  WARNING: {team_name} only has {len(starters)} starters")

            formation = _infer_formation(starters)

            results[team_name] = {
                "team_name":  team_name,
                "status":     status,
                "formation":  formation,
                "players":    starters,
                "injuries":   injuries,
                "scraped_at": now,
                "source":     "rotowire",
            }
            print(f"  ✓ {team_name:30s}  {formation:8s}  {status}  ({len(starters)} starters)")

    return results


def main():
    data = scrape()
    print(f"\nScraped {len(data)} teams")
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Saved → {OUTPUT}")
    return data


if __name__ == "__main__":
    main()
