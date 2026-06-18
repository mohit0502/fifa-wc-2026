"""
Record a completed WC 2026 fixture result and refresh all frontend data.

Usage:
    python -m scripts.record_result <fixture_id> <home_score> <away_score>

Example:
    python -m scripts.record_result 1 2 0
        → Mexico 2 – 0 South Africa, marked completed, fixtures.json regenerated.
"""

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

FIXTURES = ROOT / "data" / "raw" / "wc2026_fixtures.csv"


def main() -> None:
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(1)

    fixture_id, home_score, away_score = (
        int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
    )

    df = pd.read_csv(FIXTURES)
    mask = df["fixture_id"] == fixture_id
    if not mask.any():
        print(f"Error: fixture_id {fixture_id} not found.")
        sys.exit(1)

    row = df.loc[mask].iloc[0]
    home, away = row["home_team"], row["away_team"]

    df.loc[mask, "home_score"] = home_score
    df.loc[mask, "away_score"] = away_score
    df.loc[mask, "status"] = "completed"
    df.to_csv(FIXTURES, index=False)

    print(f"  [{fixture_id}] {home} {home_score} – {away_score} {away}  → completed")
    print(f"  Saved → {FIXTURES}")

    print("\nRe-exporting frontend data...\n")
    from scripts.export_data import main as export_main
    export_main()


if __name__ == "__main__":
    main()
