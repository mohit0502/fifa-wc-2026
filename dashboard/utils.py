"""Shared data-loading helpers used by all dashboard pages."""

from pathlib import Path
import pandas as pd

ROOT = Path(__file__).parent.parent
RAW  = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"

# ── Confederation colours ────────────────────────────────────────────────────
CONF_COLORS = {
    "UEFA":     "#003399",
    "CONMEBOL": "#009900",
    "CONCACAF": "#CC3300",
    "CAF":      "#FF9900",
    "AFC":      "#CC0066",
    "OFC":      "#006666",
}

RESULT_COLORS = {"W": "#28a745", "D": "#ffc107", "L": "#dc3545"}

# ── WC 2026 group map ────────────────────────────────────────────────────────
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

TEAM_TO_GROUP = {team: grp for grp, teams in GROUPS.items() for team in teams}


# ── Loaders (all cached) ─────────────────────────────────────────────────────
import streamlit as st

@st.cache_data(ttl=300)
def load_fixtures() -> pd.DataFrame:
    df = pd.read_csv(RAW / "wc2026_fixtures.csv", parse_dates=["match_date"])
    return df

@st.cache_data(ttl=300)
def load_team_features() -> pd.DataFrame:
    return pd.read_parquet(PROC / "team_features.parquet")

@st.cache_data(ttl=300)
def load_team_form() -> pd.DataFrame:
    return pd.read_parquet(PROC / "team_form.parquet")

@st.cache_data(ttl=300)
def load_h2h() -> pd.DataFrame:
    return pd.read_parquet(PROC / "team_h2h.parquet")

@st.cache_data(ttl=300)
def load_ranking_history() -> pd.DataFrame:
    return pd.read_parquet(PROC / "ranking_history.parquet")

@st.cache_data(ttl=300)
def load_goals_dist() -> pd.DataFrame:
    return pd.read_parquet(PROC / "team_goals_dist.parquet")

@st.cache_data(ttl=300)
def load_squads() -> pd.DataFrame:
    return pd.read_csv(RAW / "wc2026_squads.csv")

@st.cache_data(ttl=300)
def load_fjelstul_goals() -> pd.DataFrame:
    df = pd.read_parquet(PROC / "fjelstul_goals.parquet")
    df["player_name"] = (df["given_name"].fillna("") + " " + df["family_name"].fillna("")).str.strip()
    return df

@st.cache_data(ttl=300)
def load_fjelstul_matches() -> pd.DataFrame:
    return pd.read_parquet(PROC / "fjelstul_matches.parquet")


# ── Group standings from completed fixtures ──────────────────────────────────

def compute_standings(fixtures: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Return {group_name: standings_df} from completed fixtures."""
    standings: dict[str, dict] = {}

    for _, f in fixtures[fixtures["status"] == "completed"].iterrows():
        grp = f["group"]
        home, away = f["home_team"], f["away_team"]
        hs, as_ = int(f["home_score"]), int(f["away_score"])

        for team in [home, away]:
            if grp not in standings:
                standings[grp] = {}
            if team not in standings[grp]:
                standings[grp][team] = dict(P=0, W=0, D=0, L=0, GF=0, GA=0, GD=0, Pts=0)

        gf_h, ga_h = hs, as_
        gf_a, ga_a = as_, hs

        for team, gf, ga in [(home, gf_h, ga_h), (away, gf_a, ga_a)]:
            s = standings[grp][team]
            s["P"] += 1; s["GF"] += gf; s["GA"] += ga; s["GD"] = s["GF"] - s["GA"]
            if gf > ga:   s["W"] += 1; s["Pts"] += 3
            elif gf == ga: s["D"] += 1; s["Pts"] += 1
            else:          s["L"] += 1

    # Fill empty groups with zero-row standings
    result = {}
    for grp, teams in GROUPS.items():
        grp_data = standings.get(grp, {})
        rows = []
        for team in teams:
            row = grp_data.get(team, dict(P=0, W=0, D=0, L=0, GF=0, GA=0, GD=0, Pts=0))
            rows.append({"Team": team, **row})
        df = pd.DataFrame(rows).sort_values(["Pts", "GD", "GF"], ascending=False)
        df.insert(0, "#", range(1, len(df) + 1))
        result[grp] = df.reset_index(drop=True)

    return result
