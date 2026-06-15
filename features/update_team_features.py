"""
Recomputes team feature snapshot after each new result is added.
Called by the daily_pipeline GitHub Actions workflow.

Also builds per-team descriptive data used by the dashboard:
  - Form last 10 with opponent, score, result
  - H2H vs all WC 2026 opponents
  - Goals distribution (scored / conceded)
  - FIFA ranking history

Writes:
  data/processed/team_features.parquet       — latest stats snapshot
  data/processed/team_form.parquet           — last 10 per team
  data/processed/team_h2h.parquet            — h2h vs WC 2026 teams
  data/processed/ranking_history.parquet     — ranking over time (WC teams)

Run:  python -m features.update_team_features
"""

import sys
from pathlib import Path

import pandas as pd
import numpy as np

ROOT = Path(__file__).parent.parent
PROCESSED = ROOT / "data" / "processed"
sys.path.insert(0, str(ROOT))
from ingestion.team_name_map import WC2026_TEAM_NAMES
from features.build_features import build_team_features


# ── Team form: last 10 results per team ──────────────────────────────────────

def build_team_form(n: int = 10) -> pd.DataFrame:
    results = pd.read_parquet(PROCESSED / "results_clean.parquet")
    results = results.dropna(subset=["home_score", "away_score"])

    rows = []
    for team in WC2026_TEAM_NAMES:
        mask = (results["home_team"] == team) | (results["away_team"] == team)
        recent = results[mask].sort_values("date").tail(n)
        for _, r in recent.iterrows():
            is_home = r["home_team"] == team
            opponent = r["away_team"] if is_home else r["home_team"]
            gf = int(r["home_score"] if is_home else r["away_score"])
            ga = int(r["away_score"] if is_home else r["home_score"])
            if gf > ga:
                result = "W"
            elif gf == ga:
                result = "D"
            else:
                result = "L"
            rows.append({
                "team_name":     team,
                "date":          r["date"],
                "opponent":      opponent,
                "venue":         "Home" if is_home else "Away",
                "neutral":       r["neutral_venue"],
                "goals_for":     gf,
                "goals_against": ga,
                "result":        result,
                "tournament":    r["tournament"],
                "tournament_type": r["tournament_type"],
            })

    df = pd.DataFrame(rows)
    df.to_parquet(PROCESSED / "team_form.parquet", index=False)
    print(f"team_form.parquet  →  {len(df)} rows")
    return df


# ── H2H between all WC 2026 teams ────────────────────────────────────────────

def build_h2h_matrix() -> pd.DataFrame:
    results = pd.read_parquet(PROCESSED / "results_clean.parquet")
    results = results.dropna(subset=["home_score", "away_score"])
    teams   = sorted(WC2026_TEAM_NAMES)

    rows = []
    for team_a in teams:
        for team_b in teams:
            if team_a >= team_b:
                continue
            mask = (
                ((results["home_team"] == team_a) & (results["away_team"] == team_b))
                | ((results["home_team"] == team_b) & (results["away_team"] == team_a))
            )
            sub = results[mask].sort_values("date")
            n = len(sub)
            if n == 0:
                rows.append({
                    "team_a": team_a, "team_b": team_b,
                    "n_played": 0,
                    "a_wins": 0, "draws": 0, "b_wins": 0,
                    "a_goals": 0, "b_goals": 0,
                    "last_match_date": None,
                    "last_result_for_a": None,
                })
                continue

            a_wins = draws = b_wins = 0
            a_goals = b_goals = 0
            for _, r in sub.iterrows():
                if r["home_team"] == team_a:
                    gs, gc = int(r["home_score"]), int(r["away_score"])
                else:
                    gs, gc = int(r["away_score"]), int(r["home_score"])
                a_goals += gs; b_goals += gc
                if gs > gc:   a_wins += 1
                elif gs == gc: draws += 1
                else:          b_wins += 1

            last = sub.iloc[-1]
            if last["home_team"] == team_a:
                last_gs, last_gc = int(last["home_score"]), int(last["away_score"])
            else:
                last_gs, last_gc = int(last["away_score"]), int(last["home_score"])
            last_res = "W" if last_gs > last_gc else ("D" if last_gs == last_gc else "L")

            rows.append({
                "team_a":            team_a,
                "team_b":            team_b,
                "n_played":          n,
                "a_wins":            a_wins,
                "draws":             draws,
                "b_wins":            b_wins,
                "a_goals":           a_goals,
                "b_goals":           b_goals,
                "last_match_date":   last["date"],
                "last_result_for_a": last_res,
                "last_score":        f"{last_gs}–{last_gc}",
            })

    df = pd.DataFrame(rows)
    df.to_parquet(PROCESSED / "team_h2h.parquet", index=False)
    print(f"team_h2h.parquet  →  {len(df)} pairs")
    return df


# ── FIFA ranking history (WC 2026 teams only) ────────────────────────────────

def build_ranking_history() -> pd.DataFrame:
    rankings = pd.read_parquet(PROCESSED / "rankings_clean.parquet")
    wc = rankings[rankings["team_name"].isin(WC2026_TEAM_NAMES)].copy()
    wc = wc[["team_name", "rank_date", "rank", "total_points", "rank_change", "confederation"]]
    wc = wc.sort_values(["team_name", "rank_date"])
    wc.to_parquet(PROCESSED / "ranking_history.parquet", index=False)
    print(f"ranking_history.parquet  →  {len(wc)} rows, "
          f"{wc['team_name'].nunique()} WC teams")
    return wc


# ── Goals distribution per team ─────────────────────────────────────────────

def build_goals_distribution() -> pd.DataFrame:
    results = pd.read_parquet(PROCESSED / "results_clean.parquet")
    results = results.dropna(subset=["home_score", "away_score"])

    rows = []
    for team in WC2026_TEAM_NAMES:
        mask = (results["home_team"] == team) | (results["away_team"] == team)
        sub  = results[mask]
        for _, r in sub.iterrows():
            if r["home_team"] == team:
                rows.append({"team_name": team, "date": r["date"],
                              "goals_scored": int(r["home_score"]),
                              "goals_conceded": int(r["away_score"]),
                              "tournament_type": r["tournament_type"]})
            else:
                rows.append({"team_name": team, "date": r["date"],
                              "goals_scored": int(r["away_score"]),
                              "goals_conceded": int(r["home_score"]),
                              "tournament_type": r["tournament_type"]})

    df = pd.DataFrame(rows)
    df.to_parquet(PROCESSED / "team_goals_dist.parquet", index=False)
    print(f"team_goals_dist.parquet  →  {len(df)} rows")
    return df


def run_all():
    print("=" * 60)
    print("Updating team feature tables...")
    print("=" * 60)
    build_team_features()
    build_team_form()
    build_h2h_matrix()
    build_ranking_history()
    build_goals_distribution()
    print("=" * 60)
    print("Done.")


if __name__ == "__main__":
    run_all()
