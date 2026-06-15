"""
Feature engineering pipeline for the match outcome classifier and score predictor.

Reads:  data/processed/results_clean.parquet
        data/processed/rankings_clean.parquet
        data/processed/elo_clean.parquet

Writes: data/processed/training_data.parquet   — one row per match (2006+)
        data/processed/team_features.parquet   — latest snapshot per team

Run:  python -m features.build_features
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).parent.parent
PROCESSED = ROOT / "data" / "processed"
sys.path.insert(0, str(ROOT))
from ingestion.team_name_map import WC2026_TEAM_NAMES


# ── Helpers ──────────────────────────────────────────────────────────────────

def _rolling_team_stats(results: pd.DataFrame, team: str, before_date: pd.Timestamp,
                         n: int = 10) -> dict:
    """Compute rolling stats for `team` in their last n matches before `before_date`."""
    mask = (
        ((results["home_team"] == team) | (results["away_team"] == team))
        & (results["date"] < before_date)
    )
    recent = results[mask].sort_values("date").tail(n)

    if recent.empty:
        return {
            "form_win_rate": np.nan, "form_draw_rate": np.nan, "form_loss_rate": np.nan,
            "form_goals_scored": np.nan, "form_goals_conceded": np.nan,
            "form_goal_diff": np.nan,
        }

    wins = draws = losses = goals_scored = goals_conceded = 0
    for _, row in recent.iterrows():
        if row["home_team"] == team:
            gs, gc = row["home_score"], row["away_score"]
        else:
            gs, gc = row["away_score"], row["home_score"]
        goals_scored += gs
        goals_conceded += gc
        if gs > gc:
            wins += 1
        elif gs == gc:
            draws += 1
        else:
            losses += 1

    n_played = len(recent)
    return {
        "form_win_rate":       wins / n_played,
        "form_draw_rate":      draws / n_played,
        "form_loss_rate":      losses / n_played,
        "form_goals_scored":   goals_scored / n_played,
        "form_goals_conceded": goals_conceded / n_played,
        "form_goal_diff":      (goals_scored - goals_conceded) / n_played,
    }


def _get_ranking_at_date(rankings: pd.DataFrame, team: str,
                          date: pd.Timestamp) -> dict:
    """Return FIFA ranking and points for a team as-of a given date."""
    sub = rankings[(rankings["team_name"] == team) & (rankings["rank_date"] <= date)]
    if sub.empty:
        return {"fifa_rank": np.nan, "fifa_points": np.nan}
    latest = sub.sort_values("rank_date").iloc[-1]
    return {"fifa_rank": latest["rank"], "fifa_points": latest["total_points"]}


def _h2h(results: pd.DataFrame, home: str, away: str,
          before_date: pd.Timestamp, n: int = 10) -> dict:
    """Head-to-head record between two teams before a date."""
    mask = (
        (
            ((results["home_team"] == home) & (results["away_team"] == away))
            | ((results["home_team"] == away) & (results["away_team"] == home))
        )
        & (results["date"] < before_date)
    )
    sub = results[mask].sort_values("date").tail(n)
    if sub.empty:
        return {"h2h_home_wins": 0, "h2h_draws": 0, "h2h_away_wins": 0, "h2h_n": 0}

    hw = dw = aw = 0
    for _, row in sub.iterrows():
        if row["home_team"] == home:
            o = row["outcome"]
        else:
            o = {"H": "A", "A": "H", "D": "D"}[row["outcome"]]
        if o == "H":
            hw += 1
        elif o == "D":
            dw += 1
        else:
            aw += 1

    n_played = len(sub)
    return {
        "h2h_home_wins": hw / n_played,
        "h2h_draws":     dw / n_played,
        "h2h_away_wins": aw / n_played,
        "h2h_n":         n_played,
    }


# ── Main feature builder ──────────────────────────────────────────────────────

def build_training_data(cutoff_year: int = 2006) -> pd.DataFrame:
    results  = pd.read_parquet(PROCESSED / "results_clean.parquet")
    rankings = pd.read_parquet(PROCESSED / "rankings_clean.parquet")

    # Training subset: cutoff year onwards, exclude very low-importance
    train = results[
        (results["date"].dt.year >= cutoff_year)
        & (results["importance_weight"] >= 0.4)
    ].copy()

    print(f"Building features for {len(train):,} matches ({cutoff_year}+)...")

    feature_rows = []
    for _, row in train.iterrows():
        date   = row["date"]
        home   = row["home_team"]
        away   = row["away_team"]

        home_form = _rolling_team_stats(results, home, date)
        away_form = _rolling_team_stats(results, away, date)
        home_rank = _get_ranking_at_date(rankings, home, date)
        away_rank = _get_ranking_at_date(rankings, away, date)
        h2h       = _h2h(results, home, away, date)

        feature_rows.append({
            # Identifiers
            "date":             date,
            "home_team":        home,
            "away_team":        away,
            "tournament":       row["tournament"],
            "tournament_type":  row["tournament_type"],
            "neutral_venue":    row["neutral_venue"],

            # Target
            "outcome":          row["outcome"],
            "home_score":       row["home_score"],
            "away_score":       row["away_score"],

            # Sample weights
            "importance_weight": row["importance_weight"],
            "recency_weight":    row["recency_weight"],
            "sample_weight":     row["sample_weight"],

            # Home team features
            "home_form_win_rate":       home_form["form_win_rate"],
            "home_form_draw_rate":      home_form["form_draw_rate"],
            "home_form_goals_scored":   home_form["form_goals_scored"],
            "home_form_goals_conceded": home_form["form_goals_conceded"],
            "home_form_goal_diff":      home_form["form_goal_diff"],
            "home_fifa_rank":           home_rank["fifa_rank"],
            "home_fifa_points":         home_rank["fifa_points"],

            # Away team features
            "away_form_win_rate":       away_form["form_win_rate"],
            "away_form_draw_rate":      away_form["form_draw_rate"],
            "away_form_goals_scored":   away_form["form_goals_scored"],
            "away_form_goals_conceded": away_form["form_goals_conceded"],
            "away_form_goal_diff":      away_form["form_goal_diff"],
            "away_fifa_rank":           away_rank["fifa_rank"],
            "away_fifa_points":         away_rank["fifa_points"],

            # Differential features (most predictive)
            "rank_diff":        (home_rank["fifa_rank"] or 0) - (away_rank["fifa_rank"] or 0),
            "points_diff":      (home_rank["fifa_points"] or 0) - (away_rank["fifa_points"] or 0),
            "form_goal_diff_diff": (home_form["form_goal_diff"] or 0) - (away_form["form_goal_diff"] or 0),
            "form_win_diff":    (home_form["form_win_rate"] or 0) - (away_form["form_win_rate"] or 0),

            # H2H
            **h2h,
        })

    df = pd.DataFrame(feature_rows)
    df.to_parquet(PROCESSED / "training_data.parquet", index=False)
    print(f"Saved training_data.parquet  →  {len(df):,} rows, {df.shape[1]} cols")
    return df


# ── Team feature snapshot (for descriptive analytics) ────────────────────────

def build_team_features() -> pd.DataFrame:
    """Compute latest stats snapshot for every team that appears in results."""
    results  = pd.read_parquet(PROCESSED / "results_clean.parquet")
    rankings = pd.read_parquet(PROCESSED / "rankings_clean.parquet")

    today    = pd.Timestamp.today()
    # Drop rows with no result yet (future fixtures)
    results = results.dropna(subset=["home_score", "away_score"])

    all_teams = sorted(
        set(results["home_team"].tolist() + results["away_team"].tolist())
    )

    rows = []
    for team in all_teams:
        team_matches = results[
            (results["home_team"] == team) | (results["away_team"] == team)
        ]
        if team_matches.empty:
            continue

        form = _rolling_team_stats(results, team, today, n=10)
        rank = _get_ranking_at_date(rankings, team, today)

        # All-time stats
        total = len(team_matches)
        wins = draws = losses = gf = ga = 0
        for _, r in team_matches.iterrows():
            if r["home_team"] == team:
                s, c = r["home_score"], r["away_score"]
            else:
                s, c = r["away_score"], r["home_score"]
            gf += s; ga += c
            if s > c:   wins += 1
            elif s == c: draws += 1
            else:        losses += 1

        # WC appearances — count distinct years the team played in the actual WC
        # (exclude qualifiers which also match "FIFA World Cup")
        wc_matches = team_matches[team_matches["tournament_type"] == "wc"]
        wc_count = int(wc_matches["date"].dt.year.apply(
            lambda y: (y // 4) * 4  # snap to nearest WC year
        ).nunique())

        # Recent scoring (last 20 matches)
        recent20 = team_matches.sort_values("date").tail(20)
        recent_gf = recent_ga = 0
        for _, r in recent20.iterrows():
            if r["home_team"] == team:
                recent_gf += r["home_score"]; recent_ga += r["away_score"]
            else:
                recent_gf += r["away_score"]; recent_ga += r["home_score"]

        rows.append({
            "team_name":              team,
            "is_wc2026_team":         team in WC2026_TEAM_NAMES,
            "total_matches_played":   total,
            "all_time_win_rate":      wins / total if total else 0,
            "all_time_draw_rate":     draws / total if total else 0,
            "all_time_loss_rate":     losses / total if total else 0,
            "all_time_goals_for":     gf,
            "all_time_goals_against": ga,
            "all_time_goal_diff":     gf - ga,
            "avg_goals_scored_total": gf / total if total else 0,
            "avg_goals_conceded_total": ga / total if total else 0,
            "avg_goals_scored_20":    recent_gf / len(recent20) if len(recent20) else 0,
            "avg_goals_conceded_20":  recent_ga / len(recent20) if len(recent20) else 0,
            "first_match_date":       team_matches["date"].min(),
            "last_match_date":        team_matches["date"].max(),
            "wc_appearances_approx":  wc_count,
            # Form
            **{f"form_{k}": v for k, v in form.items()},
            # Ranking
            "current_fifa_rank":      rank["fifa_rank"],
            "current_fifa_points":    rank["fifa_points"],
        })

    df = pd.DataFrame(rows)
    df.to_parquet(PROCESSED / "team_features.parquet", index=False)
    print(f"Saved team_features.parquet  →  {len(df)} teams")
    return df


def run_all():
    print("=" * 60)
    print("Building feature engineering pipeline...")
    print("=" * 60)
    build_team_features()       # fast — run first for descriptive analytics
    build_training_data()       # slower — row-wise feature computation
    print("=" * 60)
    print("Done.")


if __name__ == "__main__":
    run_all()
