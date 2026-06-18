"""
Refresh WC 2026 fixture scores and regenerate all frontend data.

Re-scrapes the 12 official Wikipedia group pages (the canonical schedule
source — see scrape_official_schedule.py), which naturally picks up any
newly completed scores since the schedule itself never changes. Then
re-exports all frontend JSON and regenerates predictions.

Usage:
    python -m ingestion.fetch_live_scores
"""

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from ingestion.scrape_official_schedule import run as rebuild_schedule

FIXTURES = ROOT / "data" / "raw" / "wc2026_fixtures.csv"


def main() -> None:
    before = pd.read_csv(FIXTURES)
    n_before = int((before["status"] == "completed").sum())

    df = rebuild_schedule()
    n_after = int((df["status"] == "completed").sum())

    if n_after == n_before:
        print("\nNo new results — fixtures.csv already up to date.")
        return

    print(f"\n{n_after - n_before} new result(s) since last refresh.")

    print("\nRe-exporting frontend data...\n")
    from scripts.export_data import main as export_main
    export_main()

    print("\nRefreshing predictions...\n")
    from scripts.predict_wc2026 import main as predict_main
    predict_main()


if __name__ == "__main__":
    main()
