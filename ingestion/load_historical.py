"""
Phase 1 ingestion: load all raw CSVs → cleaned parquet files in data/processed/
Also prepares a unified matches dataframe with importance weights and sample weights.

Run:  python -m ingestion.load_historical
"""

import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).parent.parent
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
PROCESSED.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(ROOT))
from ingestion.team_name_map import normalise_series, is_wc2026_team, WC2026_TEAM_NAMES


# ── Tournament importance weights ───────────────────────────────────────────

IMPORTANCE_RULES: list[tuple[str, float]] = [
    # (regex pattern on tournament column, weight)
    (r"FIFA World Cup",                     1.5),   # group stage default; knockout boosted below
    (r"Copa América|CONMEBOL",              1.3),
    (r"UEFA Euro|European Championship",    1.3),
    (r"Africa Cup|AFCON",                   1.3),
    (r"Asian Cup|AFC Asian Cup",            1.3),
    (r"Gold Cup|CONCACAF Gold Cup",         1.2),
    (r"Nations League.*Final|UEFA Nations League Final", 1.3),
    (r"Nations League",                     1.1),
    (r"Qualifier|Qualification",            1.0),
    (r"Friendly|International",             0.4),
]

WC_KNOCKOUT_STAGES = {
    "Round of 16", "Quarter-finals", "Semi-finals", "Third-place match",
    "Final", "Round of 32", "Knockout",
}


def importance_weight(tournament: str, stage: str | None = None) -> float:
    t = str(tournament)
    for pattern, weight in IMPORTANCE_RULES:
        if re.search(pattern, t, re.IGNORECASE):
            if "FIFA World Cup" in t and stage and any(k in stage for k in WC_KNOCKOUT_STAGES):
                return 2.0
            return weight
    return 0.6  # default for unmatched tournaments


# ── Results cleaning ─────────────────────────────────────────────────────────

def load_results() -> pd.DataFrame:
    df = pd.read_csv(RAW / "results.csv", parse_dates=["date"])

    df["home_team"] = normalise_series(df["home_team"])
    df["away_team"] = normalise_series(df["away_team"])

    # Outcome label
    df["outcome"] = np.where(
        df["home_score"] > df["away_score"], "H",
        np.where(df["home_score"] < df["away_score"], "A", "D")
    )

    # Neutral venue flag
    df["neutral_venue"] = df["neutral"].astype(bool)
    df.drop(columns=["neutral"], inplace=True)

    # Tournament type classification
    df["tournament_type"] = df.apply(
        lambda r: _classify_tournament(r["tournament"]), axis=1
    )

    # Importance weight (no stage info in this dataset, so WC = 1.5 flat)
    df["importance_weight"] = df["tournament"].map(importance_weight)

    # Recency weight  λ = 0.004 (half-life ≈ 173 days)
    today = pd.Timestamp.today()
    df["days_since"] = (today - df["date"]).dt.days.clip(lower=0)
    df["recency_weight"] = np.exp(-0.004 * df["days_since"])

    df["sample_weight"] = df["recency_weight"] * df["importance_weight"]

    # WC 2026 flag
    df["is_wc_team_home"] = df["home_team"].isin(WC2026_TEAM_NAMES)
    df["is_wc_team_away"] = df["away_team"].isin(WC2026_TEAM_NAMES)

    df.to_parquet(PROCESSED / "results_clean.parquet", index=False)
    print(f"results_clean.parquet  →  {len(df):,} rows")
    return df


def _classify_tournament(t: str) -> str:
    t = str(t)
    if re.search(r"FIFA World Cup", t, re.I):
        return "wc"
    if re.search(r"Copa América|UEFA Euro|European Championship|Africa Cup|Asian Cup|Gold Cup", t, re.I):
        return "continental"
    if re.search(r"Qualifier|Qualification", t, re.I):
        return "qualifier"
    if re.search(r"Nations League", t, re.I):
        return "nations_league"
    if re.search(r"Friendly|International", t, re.I):
        return "friendly"
    return "other"


# ── Goalscorers cleaning ─────────────────────────────────────────────────────

def load_goalscorers() -> pd.DataFrame:
    df = pd.read_csv(RAW / "goalscorers.csv", parse_dates=["date"])
    df["home_team"] = normalise_series(df["home_team"])
    df["away_team"] = normalise_series(df["away_team"])
    df["team"] = normalise_series(df["team"])
    df["own_goal"] = df["own_goal"].astype(str).str.upper() == "TRUE"
    df["penalty"] = df["penalty"].astype(str).str.upper() == "TRUE"
    df.to_parquet(PROCESSED / "goalscorers_clean.parquet", index=False)
    print(f"goalscorers_clean.parquet  →  {len(df):,} rows")
    return df


# ── Shootouts cleaning ───────────────────────────────────────────────────────

def load_shootouts() -> pd.DataFrame:
    df = pd.read_csv(RAW / "shootouts.csv", parse_dates=["date"])
    df["home_team"] = normalise_series(df["home_team"])
    df["away_team"] = normalise_series(df["away_team"])
    df["winner"] = normalise_series(df["winner"])
    df.to_parquet(PROCESSED / "shootouts_clean.parquet", index=False)
    print(f"shootouts_clean.parquet  →  {len(df):,} rows")
    return df


# ── FIFA rankings cleaning ───────────────────────────────────────────────────

def load_rankings() -> pd.DataFrame:
    frames = []
    for f in sorted(RAW.glob("fifa_ranking-*.csv")):
        frames.append(pd.read_csv(f, parse_dates=["rank_date"]))
    df = pd.concat(frames, ignore_index=True)
    df["team_name"] = normalise_series(df["country_full"])
    df.drop(columns=["country_full"], inplace=True)
    df.drop_duplicates(subset=["team_name", "rank_date"], keep="last", inplace=True)
    df.sort_values(["team_name", "rank_date"], inplace=True)
    df.to_parquet(PROCESSED / "rankings_clean.parquet", index=False)
    print(f"rankings_clean.parquet  →  {len(df):,} rows, "
          f"{df['rank_date'].min().date()} → {df['rank_date'].max().date()}")
    return df


# ── Elo ratings cleaning ─────────────────────────────────────────────────────

ELO_COLS = [
    "rank", "prev_rank", "team_code", "elo",
    "rank_1yr", "elo_1yr", "rank_5yr", "elo_5yr",
    "rank_10yr", "elo_10yr",
    "chg_1m", "elo_chg_1m", "chg_3m", "elo_chg_3m",
    "chg_1yr", "elo_chg_1yr", "chg_3yr", "elo_chg_3yr",
    "chg_5yr", "elo_chg_5yr", "chg_10yr", "elo_chg_10yr",
    "chg_20yr", "elo_chg_20yr",
    "matches", "wins", "draws", "losses",
    "wc_matches", "wc_wins", "wc_draws",
    "total_matches", "total_wins",
]

# 3-letter FIFA codes → canonical names for ELO dataset
ELO_CODE_MAP = {
    "ES": "Spain", "AR": "Argentina", "FR": "France", "EN": "England",
    "BR": "Brazil", "NE": "Netherlands", "PT": "Portugal", "DE": "Germany",
    "IT": "Italy", "BE": "Belgium", "UR": "Uruguay", "CO": "Colombia",
    "ME": "Mexico", "US": "United States", "CA": "Canada", "MO": "Morocco",
    "SE": "Senegal", "JA": "Japan", "KO": "South Korea", "AU": "Australia",
    "IR": "Iran", "SA": "Saudi Arabia", "QA": "Qatar", "JO": "Jordan",
    "UZ": "Uzbekistan", "CH": "Croatia", "DK": "Denmark", "SW": "Switzerland",
    "PO": "Poland", "SC": "Scotland", "SL": "Slovakia", "CZ": "Czech Republic",
    "AU2": "Austria", "SB": "Serbia", "UK": "Ukraine", "TU": "Turkey",
    "GH": "Ghana", "EG": "Egypt", "CM": "Cameroon", "TN": "Tunisia",
    "ML": "Mali", "SA2": "South Africa", "CD": "DR Congo",
    "NZ": "New Zealand", "PA": "Paraguay", "EC": "Ecuador",
    "JM": "Jamaica", "PA2": "Panama", "HO": "Honduras", "VE": "Venezuela",
    "IN": "Indonesia",
}


def load_elo() -> pd.DataFrame:
    raw = pd.read_csv(
        RAW / "elo" / "elo_ratings_current.tsv",
        sep="\t", header=None,
        names=ELO_COLS[:min(len(ELO_COLS), 35)],
        on_bad_lines="skip",
    )
    # Clean numeric columns — remove +/− signs
    for col in raw.columns:
        if col not in ("team_code",):
            raw[col] = (
                raw[col].astype(str)
                .str.replace(r"[+−–]", lambda m: "" if m.group() == "+" else "-", regex=True)
                .str.replace(",", "", regex=False)
            )
            raw[col] = pd.to_numeric(raw[col], errors="coerce")

    raw["team_code"] = raw["team_code"].astype(str).str.strip()
    raw["team_name"] = raw["team_code"].map(
        lambda c: ELO_CODE_MAP.get(c, c)
    )
    raw["snapshot_date"] = pd.Timestamp.today().date()
    raw.to_parquet(PROCESSED / "elo_clean.parquet", index=False)
    print(f"elo_clean.parquet  →  {len(raw):,} rows")
    return raw


# ── Fjelstul data cleaning ───────────────────────────────────────────────────

def load_fjelstul() -> dict[str, pd.DataFrame]:
    fjelstul_csv = RAW / "fjelstul" / "data-csv"
    tables = {}
    team_cols = ["home_team_name", "away_team_name", "team_name",
                 "home_team", "away_team"]

    for csv_path in sorted(fjelstul_csv.glob("*.csv")):
        df = pd.read_csv(csv_path, low_memory=False)
        for col in team_cols:
            if col in df.columns:
                df[col] = normalise_series(df[col])
        tables[csv_path.stem] = df

    # Save key tables as parquet
    for name in ["matches", "goals", "squads", "players",
                 "player_appearances", "group_standings",
                 "penalty_kicks", "bookings"]:
        if name in tables:
            out = PROCESSED / f"fjelstul_{name}.parquet"
            tables[name].to_parquet(out, index=False)
            print(f"fjelstul_{name}.parquet  →  {len(tables[name]):,} rows")

    return tables


# ── Main ─────────────────────────────────────────────────────────────────────

def run_all():
    print("=" * 60)
    print("Loading and cleaning all historical data...")
    print("=" * 60)
    load_results()
    load_goalscorers()
    load_shootouts()
    load_rankings()
    load_elo()
    load_fjelstul()
    print("=" * 60)
    print("Done. All clean files written to data/processed/")


if __name__ == "__main__":
    run_all()
