"""
Generate Dixon-Coles match predictions for all 72 WC 2026 fixtures.

Usage:
    python -m scripts.predict_wc2026

Outputs:
    data/processed/wc2026_predictions.json
    frontend/public/data/predictions.json
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from models.poisson import DixonColesModel

PROCESSED  = ROOT / "data" / "processed"
ARTIFACTS  = ROOT / "models" / "artifacts"
FIXTURES   = ROOT / "data" / "raw" / "wc2026_fixtures.csv"
OUT_PROC   = PROCESSED / "wc2026_predictions.json"
OUT_FE     = ROOT / "frontend" / "public" / "data" / "predictions.json"

# WC 2026 is played in USA, Canada, Mexico — no traditional home team
NEUTRAL = True


def main() -> None:
    print("Loading model...")
    model = DixonColesModel.load(ARTIFACTS / "dc_model.pkl")

    print("Loading fixtures...")
    fx = pd.read_csv(FIXTURES, parse_dates=["match_date"])

    predictions: dict[int, dict] = {}
    no_data: list[str] = []

    print(f"\nGenerating predictions for {len(fx)} fixtures...\n")
    for _, row in fx.iterrows():
        fid  = int(row["fixture_id"])
        home = str(row["home_team"])
        away = str(row["away_team"])
        date = str(row["match_date"])[:10]

        pred = model.predict(home, away, neutral=NEUTRAL)

        # Flag teams with no model parameters (fell back to global mean 0)
        for t in (home, away):
            if t not in model.alpha:
                no_data.append(t)

        predictions[fid] = {
            "fixture_id":        fid,
            "home_team":         home,
            "away_team":         away,
            "match_date":        date,
            "home_win":          pred["home_win"],
            "draw":              pred["draw"],
            "away_win":          pred["away_win"],
            "lambda_home":       pred["lambda_home"],
            "lambda_away":       pred["lambda_away"],
            "most_likely_score": pred["most_likely_score"],
            "score_probs":       pred["score_probs"],
        }

        hw = pred["home_win"]
        dr = pred["draw"]
        aw = pred["away_win"]
        print(
            f"  [{fid:2d}] {home:25s} vs {away:25s}"
            f"  →  {hw:.0%} / {dr:.0%} / {aw:.0%}"
            f"  ({pred['most_likely_score']})"
        )

    if no_data:
        print(f"\nWarning: no model params for: {sorted(set(no_data))}")
        print("         These teams used the global mean (alpha=0, beta=0).")

    now = datetime.now(timezone.utc).isoformat()
    output = {
        "generated_at": now,
        "model":        "dixon_coles_v1",
        "n_teams":      len(model.teams),
        "fixtures":     predictions,
    }

    for path in (OUT_PROC, OUT_FE):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(output, f, separators=(",", ":"))
        size_kb = path.stat().st_size // 1024
        print(f"\nSaved → {path}  ({size_kb} KB)")

    print("\nDone.")


if __name__ == "__main__":
    main()
