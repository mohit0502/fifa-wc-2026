"""
Export all processed parquet/CSV data to JSON files consumed by the Next.js frontend.

Usage:
    python -m scripts.export_data

Output: frontend/public/data/*.json
"""

import json
import re
import sys
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

PROC = ROOT / "data" / "processed"
RAW  = ROOT / "data" / "raw"
OUT  = ROOT / "frontend" / "public" / "data"
OUT.mkdir(parents=True, exist_ok=True)

from ingestion.team_name_map import WC2026_TEAMS, WC2026_TEAM_NAMES


# ── helpers ───────────────────────────────────────────────────────────────────

def slugify(name: str) -> str:
    name = unicodedata.normalize("NFD", name)
    name = "".join(c for c in name if unicodedata.category(c) != "Mn")
    name = name.lower()
    name = re.sub(r"[^a-z0-9]+", "-", name)
    return name.strip("-")


def to_json(obj, path: Path) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, separators=(",", ":"), default=_json_default)
    print(f"  ✓ {path.name}  ({path.stat().st_size // 1024} KB)")


def _json_default(obj):
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return None if np.isnan(obj) else float(obj)
    if isinstance(obj, (pd.Timestamp, np.datetime64)):
        return str(obj)[:10]
    if isinstance(obj, float) and np.isnan(obj):
        return None
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def df_to_records(df: pd.DataFrame) -> list:
    return json.loads(df.to_json(orient="records", date_format="iso"))


# ── groups + fixtures ─────────────────────────────────────────────────────────

GROUPS = {
    "Group A": ["Czech Republic", "Mexico", "South Africa", "South Korea"],
    "Group B": ["Bosnia and Herzegovina", "Canada", "Qatar", "Switzerland"],
    "Group C": ["Brazil", "Haiti", "Morocco", "Scotland"],
    "Group D": ["Australia", "Paraguay", "Turkey", "United States"],
    "Group E": ["Curaçao", "Ecuador", "Germany", "Ivory Coast"],
    "Group F": ["Japan", "Netherlands", "Sweden", "Tunisia"],
    "Group G": ["Belgium", "Egypt", "Iran", "New Zealand"],
    "Group H": ["Cape Verde", "Saudi Arabia", "Spain", "Uruguay"],
    "Group I": ["France", "Iraq", "Norway", "Senegal"],
    "Group J": ["Algeria", "Argentina", "Austria", "Jordan"],
    "Group K": ["Colombia", "DR Congo", "Portugal", "Uzbekistan"],
    "Group L": ["Croatia", "England", "Ghana", "Panama"],
}

TEAM_TO_GROUP: dict[str, str] = {
    team: grp for grp, teams in GROUPS.items() for team in teams
}


def export_fixtures():
    df = pd.read_csv(RAW / "wc2026_fixtures.csv", parse_dates=["match_date"])
    df["match_date"] = df["match_date"].dt.strftime("%Y-%m-%d")
    df["home_score"] = df["home_score"].where(df["home_score"].notna(), None)
    df["away_score"] = df["away_score"].where(df["away_score"].notna(), None)
    records = df_to_records(df)
    to_json(records, OUT / "fixtures.json")


def export_groups():
    """Export group structure with team slugs for the frontend."""
    out = {}
    for grp, teams in GROUPS.items():
        letter = grp.split()[-1]
        out[letter] = {
            "label": grp,
            "teams": [{"name": t, "slug": slugify(t), "conf": WC2026_TEAMS.get(t, "")} for t in teams],
        }
    to_json(out, OUT / "groups.json")


# ── squads ────────────────────────────────────────────────────────────────────

def export_squads():
    df = pd.read_csv(RAW / "wc2026_squads.csv")
    df = df[df["team_name"].isin(WC2026_TEAM_NAMES)].copy()
    df["slug"] = df["team_name"].apply(slugify)

    # Replace NaN with None for JSON
    df = df.where(pd.notnull(df), None)

    # Group by team slug
    squads: dict = {}
    for slug, grp in df.groupby("slug"):
        team_name = grp["team_name"].iloc[0]
        players = grp[[
            "squad_number", "position", "player_name",
            "date_of_birth", "age", "caps", "international_goals",
            "club", "club_country",
        ]].to_dict("records")
        squads[slug] = {
            "team_name": team_name,
            "slug": slug,
            "group": TEAM_TO_GROUP.get(team_name, ""),
            "conf": WC2026_TEAMS.get(team_name, ""),
            "players": players,
        }

    to_json(squads, OUT / "squads.json")


# ── team form ─────────────────────────────────────────────────────────────────

def export_form():
    df = pd.read_parquet(PROC / "team_form.parquet")
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    df = df.where(pd.notnull(df), None)
    df["slug"] = df["team_name"].apply(slugify)

    form: dict = {}
    for slug, grp in df.groupby("slug"):
        rows = grp.sort_values("date").tail(10)[[
            "date", "opponent", "venue", "goals_for", "goals_against", "result", "tournament",
        ]].to_dict("records")
        form[slug] = rows

    to_json(form, OUT / "form.json")


# ── ranking history ───────────────────────────────────────────────────────────

def export_rankings():
    df = pd.read_parquet(PROC / "ranking_history.parquet")
    df["rank_date"] = pd.to_datetime(df["rank_date"]).dt.strftime("%Y-%m-%d")
    df = df.where(pd.notnull(df), None)
    df["slug"] = df["team_name"].apply(slugify)

    rankings: dict = {}
    for slug, grp in df.groupby("slug"):
        rows = grp.sort_values("rank_date").tail(20)[[
            "rank_date", "rank", "total_points",
        ]].to_dict("records")
        rankings[slug] = rows

    to_json(rankings, OUT / "rankings.json")


# ── H2H ───────────────────────────────────────────────────────────────────────

def export_h2h():
    df = pd.read_parquet(PROC / "team_h2h.parquet")
    df["last_match_date"] = pd.to_datetime(df["last_match_date"]).dt.strftime("%Y-%m-%d")
    df = df.where(pd.notnull(df), None)
    df["slug_a"] = df["team_a"].apply(slugify)
    df["slug_b"] = df["team_b"].apply(slugify)
    records = df_to_records(df)
    to_json(records, OUT / "h2h.json")


# ── team features snapshot ────────────────────────────────────────────────────

def export_team_features():
    df = pd.read_parquet(PROC / "team_features.parquet")
    df = df[df["team_name"].isin(WC2026_TEAM_NAMES)].copy()
    df = df.where(pd.notnull(df), None)
    df["slug"] = df["team_name"].apply(slugify)
    df["group"] = df["team_name"].map(TEAM_TO_GROUP)
    df["conf"]  = df["team_name"].map(WC2026_TEAMS)

    # Latest FIFA ranking for each team from rankings
    try:
        rank_df = pd.read_parquet(PROC / "ranking_history.parquet")
        latest_rank = (
            rank_df.sort_values("rank_date")
            .groupby("team_name")
            .last()["rank"]
            .to_dict()
        )
        df["fifa_rank"] = df["team_name"].map(latest_rank)
    except Exception:
        df["fifa_rank"] = None

    features: dict = {}
    for _, row in df.iterrows():
        slug = row["slug"]
        features[slug] = {k: (None if (isinstance(v, float) and np.isnan(v)) else v)
                          for k, v in row.to_dict().items()}

    to_json(features, OUT / "team_features.json")


# ── historical WC scorers ─────────────────────────────────────────────────────

def export_wc_scorers():
    try:
        df = pd.read_parquet(PROC / "fjelstul_goals.parquet")
        df["player_name"] = (
            df["given_name"].fillna("") + " " + df["family_name"].fillna("")
        ).str.strip()
        scorers = (
            df[df["own_goal"] == 0]
            .groupby(["player_name", "team_name"])["goal_id"]
            .count()
            .reset_index(name="wc_goals")
            .sort_values("wc_goals", ascending=False)
            .head(50)
        )
        scorers = scorers.where(pd.notnull(scorers), None)
        to_json(scorers.to_dict("records"), OUT / "wc_scorers.json")
    except Exception as e:
        print(f"  ! wc_scorers skipped: {e}")
        to_json([], OUT / "wc_scorers.json")


# ── player summary stats for analytics page ───────────────────────────────────

def export_player_summary():
    df = pd.read_csv(RAW / "wc2026_squads.csv")
    df = df[df["team_name"].isin(WC2026_TEAM_NAMES)].copy()
    df = df.where(pd.notnull(df), None)
    df["conf"] = df["team_name"].map(WC2026_TEAMS)

    # Position breakdown
    pos_counts = df["position"].value_counts().to_dict()

    # Top clubs
    top_clubs = (
        df[df["club"].notna()]
        .groupby("club").size()
        .sort_values(ascending=False)
        .head(30)
        .reset_index()
        .rename(columns={0: "count"})
        .to_dict("records")
    )

    # Top club countries
    top_club_countries = (
        df[df["club_country"].notna()]
        .groupby("club_country").size()
        .sort_values(ascending=False)
        .head(20)
        .reset_index()
        .rename(columns={0: "count"})
        .to_dict("records")
    )

    # Avg squad age per team
    squad_age = (
        df[df["age"].notna()]
        .groupby("team_name")["age"]
        .agg(["mean", "min", "max"])
        .round(1)
        .reset_index()
        .rename(columns={"mean": "avg_age", "min": "min_age", "max": "max_age"})
        .to_dict("records")
    )

    # Top caps
    top_caps = (
        df[df["caps"].notna()]
        .nlargest(30, "caps")[[
            "player_name", "team_name", "position", "age", "caps", "international_goals",
        ]]
        .to_dict("records")
    )

    # Top international scorers
    top_scorers = (
        df[df["international_goals"].notna() & (df["international_goals"] > 0)]  # type: ignore[operator]
        .nlargest(30, "international_goals")[[
            "player_name", "team_name", "position", "caps", "international_goals",
        ]]
        .to_dict("records")
    )

    # Confederation position breakdown
    conf_pos = (
        df[df["position"].notna() & df["conf"].notna()]
        .groupby(["conf", "position"]).size()
        .reset_index(name="count")
        .to_dict("records")
    )

    summary = {
        "total_players": len(df),
        "total_teams": df["team_name"].nunique(),
        "total_clubs": int(df["club"].nunique()),
        "avg_age": round(float(df["age"].dropna().mean()), 1),
        "avg_caps": round(float(df["caps"].dropna().mean()), 1),
        "pos_counts": pos_counts,
        "top_clubs": top_clubs,
        "top_club_countries": top_club_countries,
        "squad_age": squad_age,
        "top_caps": top_caps,
        "top_scorers": top_scorers,
        "conf_pos": conf_pos,
    }
    to_json(summary, OUT / "player_summary.json")


# ── lineups (predicted XIs from RotoWire) ────────────────────────────────────

def export_lineups():
    lineup_file = RAW / "lineups.json"
    if not lineup_file.exists():
        print("  ! lineups.json not found — run ingestion/scrape_lineups.py first")
        to_json({}, OUT / "lineups.json")
        return
    with open(lineup_file, encoding="utf-8") as f:
        data = json.load(f)
    # Key by slug
    by_slug = {slugify(team): info for team, info in data.items()}
    to_json(by_slug, OUT / "lineups.json")


# ── team meta (for navbar / search) ──────────────────────────────────────────

def export_team_meta():
    teams = []
    for team, conf in sorted(WC2026_TEAMS.items()):
        teams.append({
            "name": team,
            "slug": slugify(team),
            "conf": conf,
            "group": TEAM_TO_GROUP.get(team, ""),
        })
    to_json(teams, OUT / "teams_meta.json")


# ── run all ───────────────────────────────────────────────────────────────────

def main():
    print(f"\nExporting data → {OUT}\n")
    export_groups()
    export_fixtures()
    export_squads()
    export_form()
    export_rankings()
    export_h2h()
    export_team_features()
    export_lineups()
    export_wc_scorers()
    export_player_summary()
    export_team_meta()
    print("\nDone.")


if __name__ == "__main__":
    main()
