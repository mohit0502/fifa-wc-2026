"""
Train the Dixon-Coles Poisson model on historical international match data.

Usage:
    python -m models.train

Output: models/artifacts/dc_model.pkl
"""

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from models.poisson import DixonColesModel
from ingestion.team_name_map import WC2026_TEAM_NAMES

PROCESSED  = ROOT / "data" / "processed"
ARTIFACTS  = ROOT / "models" / "artifacts"


def main() -> None:
    print("=" * 60)
    print("Dixon-Coles Poisson Model — Training")
    print("=" * 60)

    # ── Load data ─────────────────────────────────────────────────────────────
    print("\nLoading results_clean.parquet...")
    results = pd.read_parquet(PROCESSED / "results_clean.parquet")

    # Drop future / scoreless rows
    df = results.dropna(subset=["home_score", "away_score"]).copy()

    # Training window: 2006 onwards, exclude very low-importance friendlies
    df = df[
        (df["date"].dt.year >= 2006)
        & (df["importance_weight"] >= 0.4)
    ].copy()

    print(f"Training rows: {len(df):,}  ({df['date'].dt.year.min()}–{df['date'].dt.year.max()})")
    print(f"Tournament types:\n{df['tournament_type'].value_counts().to_string()}")

    # ── Team list ─────────────────────────────────────────────────────────────
    # All WC 2026 teams + any team appearing ≥15 times (stable parameter estimates)
    team_counts = pd.concat([df["home_team"], df["away_team"]]).value_counts()
    frequent    = set(team_counts[team_counts >= 15].index)
    team_list   = sorted(set(WC2026_TEAM_NAMES) | frequent)

    wc_in_list  = [t for t in WC2026_TEAM_NAMES if t in team_list]
    wc_missing  = [t for t in WC2026_TEAM_NAMES if t not in team_list]

    print(f"\nTeam list: {len(team_list)} total")
    print(f"  WC 2026 teams covered: {len(wc_in_list)}/48")
    if wc_missing:
        print(f"  Missing (will use global mean):  {wc_missing}")

    # ── Fit ───────────────────────────────────────────────────────────────────
    print("\nFitting model...")
    model = DixonColesModel()
    model.fit(df, team_list)

    # ── Diagnostics ───────────────────────────────────────────────────────────
    print(f"\nHome advantage γ = {model.gamma:.3f}  "
          f"(exp={round(float(__import__('numpy').exp(model.gamma)), 3)}× goal boost)")
    print(f"DC correlation  ρ = {model.rho:.3f}")

    params = model.team_params()
    wc_params = params[params["team"].isin(WC2026_TEAM_NAMES)]

    print("\nTop 10 attack (WC teams):")
    print(wc_params.nlargest(10, "attack")[["team", "attack"]].to_string(index=False))
    print("\nTop 10 defense (WC teams, lower beta = harder to score against):")
    print(wc_params.nsmallest(10, "defense")[["team", "defense"]].to_string(index=False))

    # Spot-check a marquee fixture
    check = ("France", "Brazil")
    if all(t in model.alpha for t in check):
        pred = model.predict(*check, neutral=True)
        print(f"\nSpot-check  {check[0]} vs {check[1]} (neutral):")
        print(f"  {check[0]} win {pred['home_win']:.1%}  "
              f"Draw {pred['draw']:.1%}  "
              f"{check[1]} win {pred['away_win']:.1%}")
        print(f"  xG: {pred['lambda_home']} – {pred['lambda_away']}")
        print(f"  Most likely: {pred['most_likely_score']}")

    # ── Save ──────────────────────────────────────────────────────────────────
    model.save(ARTIFACTS / "dc_model.pkl")
    print("\nDone.\n")


if __name__ == "__main__":
    main()
