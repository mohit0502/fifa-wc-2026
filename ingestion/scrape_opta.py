"""
Scrape Opta supercomputer pre-tournament predictions (static, scraped once).

Sources tried in order:
  1. theanalyst.com 2026 WC prediction article
  2. BBC Sport supercomputer

Output: data/raw/opta_predictions.json

Usage:
  python -m ingestion.scrape_opta
"""

import json
import re
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
from ingestion.team_name_map import normalise

OUTPUT = ROOT / "data" / "raw" / "opta_predictions.json"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

ANALYST_URL = (
    "https://theanalyst.com/articles/"
    "who-will-win-2026-fifa-world-cup-predictions-opta-supercomputer"
)


def _parse_percent(text: str) -> float | None:
    m = re.search(r"([\d.]+)\s*%", text)
    return float(m.group(1)) / 100 if m else None


def _scrape_theanalyst() -> list[dict]:
    print(f"Fetching {ANALYST_URL}")
    try:
        resp = requests.get(ANALYST_URL, headers=HEADERS, timeout=20)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"  ERROR: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    records = []

    # Look for tables with team probabilities
    for table in soup.find_all("table"):
        headers = [th.get_text(strip=True).lower() for th in table.find_all("th")]
        if not any("team" in h or "country" in h for h in headers):
            continue

        col_map = {}
        for i, h in enumerate(headers):
            if "team" in h or "country" in h:
                col_map["team"] = i
            elif "win" in h or "champion" in h:
                col_map["win_tournament"] = i
            elif "final" in h:
                col_map["reach_final"] = i
            elif "semi" in h:
                col_map["reach_semi"] = i
            elif "quarter" in h or "qf" in h:
                col_map["reach_qf"] = i
            elif "group" in h or "r32" in h or "knockout" in h:
                col_map["advance_group"] = i

        for tr in table.find_all("tr")[1:]:
            cells = tr.find_all(["td", "th"])
            if not cells:
                continue
            team_idx = col_map.get("team", 0)
            if team_idx >= len(cells):
                continue
            team = normalise(cells[team_idx].get_text(strip=True))
            if not team:
                continue

            row = {"team_name": team}
            for key, idx in col_map.items():
                if key == "team" or idx >= len(cells):
                    continue
                row[key] = _parse_percent(cells[idx].get_text(strip=True))
            records.append(row)

    # Fallback: look for percentage patterns in paragraphs / divs
    if not records:
        text_blocks = soup.find_all(["p", "li", "div"], string=re.compile(r"\d+\s*%"))
        for block in text_blocks:
            text = block.get_text(strip=True)
            pct = _parse_percent(text)
            if pct and pct > 0.01:
                # Try to find team name near percentage
                # Heuristic: first capitalised word run before the %
                m = re.search(r"([A-Z][a-zA-Z\s]+?)\s+[\d.]+\s*%", text)
                if m:
                    team = normalise(m.group(1).strip())
                    records.append({"team_name": team, "win_tournament": pct})

    return records


def run():
    records = _scrape_theanalyst()

    if not records:
        print("No data extracted from theanalyst.com — saving empty stub.")
        records = []

    output = {
        "source": "Opta supercomputer via theanalyst.com",
        "url": ANALYST_URL,
        "scraped_date": str(__import__("datetime").date.today()),
        "note": "Static pre-tournament probabilities. Re-scrape not needed.",
        "predictions": records,
    }

    with open(OUTPUT, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Saved {len(records)} team predictions → {OUTPUT}")
    if records:
        for r in sorted(records, key=lambda x: -(x.get("win_tournament") or 0))[:10]:
            print(f"  {r['team_name']:20s}  win={r.get('win_tournament', 'N/A')}")


if __name__ == "__main__":
    run()
