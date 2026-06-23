"""
Refresh WC 2026 fixture scores from the SportAPI7 (Sofascore) live feed and
regenerate all frontend data.

Pulls football fixtures scheduled for each WC 2026 match date from
SportAPI7 (https://rapidapi.com/rapidsportapi/api/sportapi7, free "BASIC"
plan via RapidAPI), filters to tournament.uniqueTournament.name ==
"FIFA World Cup", matches them to our local fixtures by (home_team,
away_team) using the canonical team name map, and updates scores/status
in place. The schedule itself (dates, venues, groups) is left untouched —
only scores/status change.

Requires the SPORTAPI7_KEY environment variable (a RapidAPI key
subscribed to the SportAPI7 free plan).

Usage:
    python -m ingestion.fetch_live_scores
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from ingestion.team_name_map import normalise

FIXTURES = ROOT / "data" / "raw" / "wc2026_fixtures.csv"

API_HOST = "sportapi7.p.rapidapi.com"
API_BASE = f"https://{API_HOST}/api/v1"
TOURNAMENT_NAME = "FIFA World Cup"

# Sofascore event.status.type values that mean "still in progress".
LIVE_STATUS_TYPES = {"inprogress"}
FINISHED_STATUS_TYPES = {"finished"}


def fetch_events_for_date(date: str, api_key: str) -> list[dict]:
    resp = requests.get(
        f"{API_BASE}/sport/football/scheduled-events/{date}",
        headers={"X-RapidAPI-Key": api_key, "X-RapidAPI-Host": API_HOST},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json().get("events", [])


def fetch_wc2026_events(dates: list[str], api_key: str) -> list[dict]:
    events = []
    for date in dates:
        for event in fetch_events_for_date(date, api_key):
            tournament_name = event.get("tournament", {}).get("uniqueTournament", {}).get("name")
            if tournament_name == TOURNAMENT_NAME:
                events.append(event)
    return events


def run() -> pd.DataFrame:
    api_key = os.environ.get("SPORTAPI7_KEY")
    if not api_key:
        raise RuntimeError("SPORTAPI7_KEY environment variable is not set.")

    df = pd.read_csv(FIXTURES)

    # Only poll today and yesterday (UTC) — covers any match currently live
    # or one that finished just after midnight UTC — instead of re-fetching
    # every match date on every run, which would waste the free quota.
    today = datetime.now(timezone.utc).date()
    dates = [str(today), str(today - timedelta(days=1))]
    events = fetch_wc2026_events(dates, api_key)

    # Index API events by normalised (home, away) team names.
    by_teams: dict[tuple[str, str], dict] = {}
    for event in events:
        home = normalise(event["homeTeam"]["name"])
        away = normalise(event["awayTeam"]["name"])
        by_teams[(home, away)] = event

    n_updated = 0
    for idx, row in df.iterrows():
        key = (normalise(row["home_team"]), normalise(row["away_team"]))
        event = by_teams.get(key)
        if event is None:
            continue

        status_type = event.get("status", {}).get("type")
        home_score = event.get("homeScore", {}).get("current")
        away_score = event.get("awayScore", {}).get("current")

        if status_type in FINISHED_STATUS_TYPES:
            new_status = "completed"
        elif status_type in LIVE_STATUS_TYPES:
            new_status = "live"
        else:
            new_status = row["status"]  # not started yet, leave as-is

        changed = (
            new_status != row["status"]
            or home_score != row["home_score"]
            or away_score != row["away_score"]
        )
        if changed and home_score is not None and away_score is not None:
            df.at[idx, "home_score"] = home_score
            df.at[idx, "away_score"] = away_score
            df.at[idx, "status"] = new_status
            n_updated += 1

    df.to_csv(FIXTURES, index=False)
    print(f"Updated {n_updated} fixture(s) from SportAPI7.")
    return df


def main() -> None:
    before = pd.read_csv(FIXTURES)
    n_before_completed = int((before["status"] == "completed").sum())
    n_before_live = int((before["status"] == "live").sum())

    df = run()

    n_after_completed = int((df["status"] == "completed").sum())
    n_after_live = int((df["status"] == "live").sum())

    if n_after_completed == n_before_completed and n_after_live == n_before_live:
        print("\nNo status changes — fixtures.csv already up to date.")
        return

    print(
        f"\n{n_after_completed - n_before_completed} newly completed, "
        f"{n_after_live} currently live."
    )

    print("\nRe-exporting frontend data...\n")
    from scripts.export_data import main as export_main
    export_main()

    print("\nRefreshing predictions...\n")
    from scripts.predict_wc2026 import main as predict_main
    predict_main()


if __name__ == "__main__":
    main()
