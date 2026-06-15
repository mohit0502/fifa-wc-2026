"""
Player Analytics — pure visualisations, no model required.

Sections:
  1. Tournament at a glance (squad sizes, age, position breakdown)
  2. Age profiles — oldest/youngest squads
  3. Club representation — which clubs sent the most players
  4. Club country / league concentration
  5. Caps — most experienced players
  6. International goals leaders
  7. Historical WC scorers (Fjelstul DB, 1930–2022)
  8. Squad depth by position per team
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from dashboard.utils import (
    load_squads, load_fjelstul_goals, load_fjelstul_matches,
    CONF_COLORS,
)
from ingestion.team_name_map import WC2026_TEAMS, WC2026_TEAM_NAMES

st.set_page_config(
    page_title="WC 2026 — Player Analytics",
    page_icon="👤",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("WC 2026")
    st.page_link("pages/01_tournament_overview.py", label="🏆 Tournament Overview")
    st.page_link("pages/05_player_analytics.py",   label="👤 Player Analytics")
    st.divider()
    st.caption("Filter options")
    conf_filter = st.multiselect(
        "Confederation",
        options=["UEFA", "CONMEBOL", "CONCACAF", "CAF", "AFC", "OFC"],
        default=["UEFA", "CONMEBOL", "CONCACAF", "CAF", "AFC", "OFC"],
    )
    pos_filter = st.multiselect(
        "Position",
        options=["GK", "DEF", "MID", "FWD"],
        default=["GK", "DEF", "MID", "FWD"],
    )

# ── Load data ─────────────────────────────────────────────────────────────────
squads_all = load_squads()
fj_goals   = load_fjelstul_goals()

squads_wc = squads_all[squads_all["team_name"].isin(WC2026_TEAM_NAMES)].copy()
squads_wc["confederation"] = squads_wc["team_name"].map(WC2026_TEAMS)

# Apply filters
if conf_filter:
    squads_wc = squads_wc[squads_wc["confederation"].isin(conf_filter)]
if pos_filter:
    squads_wc = squads_wc[squads_wc["position"].isin(pos_filter) | squads_wc["position"].isna()]

# ── Header ─────────────────────────────────────────────────────────────────────
st.title("👤 Player Analytics — WC 2026")
st.caption(f"Showing {len(squads_wc)} players across {squads_wc['team_name'].nunique()} teams")

# ── Top-level metrics ──────────────────────────────────────────────────────────
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Players",       len(squads_wc))
m2.metric("Teams",         squads_wc["team_name"].nunique())
m3.metric("Clubs represented", squads_wc["club"].nunique())
m4.metric("Avg age",       f"{squads_wc['age'].mean():.1f}")
m5.metric("Avg caps",      f"{squads_wc['caps'].mean():.0f}")

st.divider()

# ════════════════════════════════════════════════════════════════════════════
# SECTION 1 — Position breakdown
# ════════════════════════════════════════════════════════════════════════════
st.subheader("1 · Squad Composition by Position")
c1, c2 = st.columns([1, 1])

with c1:
    pos_counts = squads_wc["position"].value_counts().reset_index()
    pos_counts.columns = ["Position", "Count"]
    fig = px.pie(
        pos_counts, names="Position", values="Count",
        title="Position split across all squads",
        color="Position",
        color_discrete_map={"GK": "#4e79a7", "DEF": "#f28e2b",
                            "MID": "#59a14f", "FWD": "#e15759"},
        hole=0.4,
    )
    fig.update_traces(textinfo="percent+label")
    fig.update_layout(template="plotly_white", height=350, showlegend=True)
    st.plotly_chart(fig, use_container_width=True)

with c2:
    pos_conf = (
        squads_wc.groupby(["confederation", "position"])
        .size().reset_index(name="count")
    )
    fig2 = px.bar(
        pos_conf, x="confederation", y="count", color="position",
        title="Position split by confederation",
        barmode="stack", template="plotly_white",
        color_discrete_map={"GK": "#4e79a7", "DEF": "#f28e2b",
                            "MID": "#59a14f", "FWD": "#e15759"},
        labels={"confederation": "Confederation", "count": "Players"},
    )
    fig2.update_layout(height=350, legend_title="Position")
    st.plotly_chart(fig2, use_container_width=True)

# ════════════════════════════════════════════════════════════════════════════
# SECTION 2 — Age profiles
# ════════════════════════════════════════════════════════════════════════════
st.divider()
st.subheader("2 · Age Profiles")
c1, c2 = st.columns([1.2, 1])

with c1:
    squad_age = (
        squads_wc.groupby("team_name")["age"]
        .agg(["mean", "min", "max"])
        .reset_index()
        .rename(columns={"mean": "avg_age", "min": "min_age", "max": "max_age"})
        .sort_values("avg_age", ascending=False)
    )
    squad_age["confederation"] = squad_age["team_name"].map(WC2026_TEAMS)

    fig = px.bar(
        squad_age, x="avg_age", y="team_name", orientation="h",
        color="confederation",
        error_x=squad_age["max_age"] - squad_age["avg_age"],
        error_x_minus=squad_age["avg_age"] - squad_age["min_age"],
        title="Average squad age (error bars = youngest/oldest player)",
        labels={"avg_age": "Avg Age", "team_name": ""},
        template="plotly_white",
        color_discrete_map=CONF_COLORS,
    )
    fig.update_layout(height=900, legend_title="Confederation",
                      yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig, use_container_width=True)

with c2:
    fig2 = px.histogram(
        squads_wc, x="age", nbins=20, color="position",
        title="Age distribution (all players)",
        template="plotly_white", barmode="overlay", opacity=0.75,
        color_discrete_map={"GK": "#4e79a7", "DEF": "#f28e2b",
                            "MID": "#59a14f", "FWD": "#e15759"},
    )
    fig2.update_layout(height=400, legend_title="Position")
    st.plotly_chart(fig2, use_container_width=True)

    # Oldest / youngest squad callouts
    oldest  = squad_age.iloc[0]
    youngest = squad_age.iloc[-1]
    st.metric("Oldest avg squad",   f"{oldest['team_name']}",  f"{oldest['avg_age']:.1f} yrs")
    st.metric("Youngest avg squad", f"{youngest['team_name']}", f"{youngest['avg_age']:.1f} yrs")

# ════════════════════════════════════════════════════════════════════════════
# SECTION 3 — Club representation
# ════════════════════════════════════════════════════════════════════════════
st.divider()
st.subheader("3 · Club Representation")
c1, c2 = st.columns([1.2, 1])

with c1:
    club_counts = (
        squads_wc[squads_wc["club"].notna()]
        .groupby("club").size()
        .reset_index(name="players")
        .sort_values("players", ascending=False)
        .head(25)
    )
    fig = px.bar(
        club_counts, x="players", y="club", orientation="h",
        title="Top 25 clubs by players at WC 2026",
        labels={"players": "Players", "club": ""},
        template="plotly_white",
        color="players", color_continuous_scale="Blues",
    )
    fig.update_layout(height=700, yaxis={"categoryorder": "total ascending"},
                      coloraxis_showscale=False)
    st.plotly_chart(fig, use_container_width=True)

with c2:
    club_country = (
        squads_wc[squads_wc["club_country"].notna()]
        .groupby("club_country").size()
        .reset_index(name="players")
        .sort_values("players", ascending=False)
        .head(20)
    )
    fig2 = px.bar(
        club_country, x="players", y="club_country", orientation="h",
        title="Players by club country (top 20 leagues)",
        labels={"players": "Players", "club_country": ""},
        template="plotly_white",
        color="players", color_continuous_scale="Teal",
    )
    fig2.update_layout(height=700, yaxis={"categoryorder": "total ascending"},
                       coloraxis_showscale=False)
    st.plotly_chart(fig2, use_container_width=True)

# ════════════════════════════════════════════════════════════════════════════
# SECTION 4 — Caps leaders
# ════════════════════════════════════════════════════════════════════════════
st.divider()
st.subheader("4 · Most Experienced Players (Caps)")
c1, c2 = st.columns([1.2, 1])

with c1:
    top_caps = (
        squads_wc[squads_wc["caps"].notna()]
        .nlargest(25, "caps")[["player_name", "team_name", "position", "age", "caps", "international_goals"]]
    )
    fig = px.scatter(
        top_caps, x="caps", y="player_name",
        color="team_name", size="international_goals",
        size_max=20,
        title="Top 25 most-capped players at WC 2026",
        labels={"caps": "International Caps", "player_name": ""},
        template="plotly_white",
        hover_data=["position", "age"],
    )
    fig.update_layout(height=700, yaxis={"categoryorder": "total ascending"},
                      legend_title="Team")
    st.plotly_chart(fig, use_container_width=True)

with c2:
    # Caps heatmap by team and position
    caps_heat = (
        squads_wc[squads_wc["position"].isin(["GK", "DEF", "MID", "FWD"])]
        .groupby(["team_name", "position"])["caps"]
        .mean()
        .unstack(fill_value=0)
        .round(0)
    )
    caps_heat["_total"] = caps_heat.sum(axis=1)
    caps_heat = caps_heat.sort_values("_total", ascending=False).drop(columns=["_total"])

    fig2 = px.imshow(
        caps_heat,
        title="Avg caps by position per team",
        labels={"x": "Position", "y": "", "color": "Avg Caps"},
        color_continuous_scale="YlOrRd",
        aspect="auto",
        text_auto=".0f",
    )
    fig2.update_layout(height=700)
    st.plotly_chart(fig2, use_container_width=True)

# ════════════════════════════════════════════════════════════════════════════
# SECTION 5 — International goals leaders (current squad)
# ════════════════════════════════════════════════════════════════════════════
st.divider()
st.subheader("5 · International Goals Leaders (2026 Squad)")

top_scorers = (
    squads_wc[squads_wc["international_goals"].notna()
              & squads_wc["international_goals"].gt(0)]
    .nlargest(30, "international_goals")
    [["player_name", "team_name", "position", "caps", "international_goals"]]
)

fig = px.bar(
    top_scorers, x="international_goals", y="player_name",
    color="team_name", orientation="h",
    title="Top 30 international goal scorers among WC 2026 players",
    labels={"international_goals": "International Goals", "player_name": ""},
    template="plotly_white",
)
fig.update_layout(height=800, yaxis={"categoryorder": "total ascending"},
                  legend_title="Team")
st.plotly_chart(fig, use_container_width=True)

# ════════════════════════════════════════════════════════════════════════════
# SECTION 6 — Historical WC goal scorers (Fjelstul DB)
# ════════════════════════════════════════════════════════════════════════════
st.divider()
st.subheader("6 · All-Time World Cup Top Scorers (1930–2022)")
c1, c2 = st.columns([1.2, 1])

with c1:
    wc_scorers = (
        fj_goals[fj_goals["own_goal"] == 0]
        .groupby(["player_name", "team_name"])["goal_id"]
        .count()
        .reset_index(name="wc_goals")
        .sort_values("wc_goals", ascending=False)
        .head(25)
    )
    fig = px.bar(
        wc_scorers, x="wc_goals", y="player_name", color="team_name",
        orientation="h",
        title="Top 25 all-time WC scorers",
        labels={"wc_goals": "WC Goals", "player_name": ""},
        template="plotly_white",
    )
    fig.update_layout(height=700, yaxis={"categoryorder": "total ascending"},
                      legend_title="Country")
    st.plotly_chart(fig, use_container_width=True)

with c2:
    # Goals by tournament edition
    goals_by_tournament = (
        fj_goals[fj_goals["own_goal"] == 0]
        .groupby("tournament_name")["goal_id"]
        .count()
        .reset_index(name="goals")
        .sort_values("tournament_name")
    )
    goals_by_tournament["year"] = goals_by_tournament["tournament_name"].str.extract(r"(\d{4})").astype(int)
    goals_by_tournament = goals_by_tournament.sort_values("year")

    fig2 = px.bar(
        goals_by_tournament, x="year", y="goals",
        title="Goals scored per WC tournament",
        labels={"year": "Year", "goals": "Goals"},
        template="plotly_white",
        color="goals", color_continuous_scale="Oranges",
    )
    fig2.update_layout(height=350, coloraxis_showscale=False)
    st.plotly_chart(fig2, use_container_width=True)

    # WC 2026 players with historical WC scoring record
    prev_scorers = (
        fj_goals[fj_goals["own_goal"] == 0]
        .groupby("player_name")["goal_id"]
        .count()
        .reset_index(name="prev_wc_goals")
    )
    returning = squads_wc.merge(
        prev_scorers, left_on="player_name", right_on="player_name", how="inner"
    )
    if not returning.empty:
        st.markdown("**WC 2026 players with previous WC goals:**")
        st.dataframe(
            returning[["team_name", "player_name", "position", "age", "prev_wc_goals"]]
            .sort_values("prev_wc_goals", ascending=False)
            .rename(columns={"prev_wc_goals": "WC goals (pre-2026)"}),
            use_container_width=True, hide_index=True,
        )
    else:
        st.caption("Name-match between 2026 squads and historical WC scorers produced no overlaps.")

# ════════════════════════════════════════════════════════════════════════════
# SECTION 7 — Squad depth heatmap
# ════════════════════════════════════════════════════════════════════════════
st.divider()
st.subheader("7 · Squad Depth by Position")

depth = (
    squads_wc[squads_wc["position"].isin(["GK", "DEF", "MID", "FWD"])]
    .groupby(["team_name", "position"])
    .size()
    .unstack(fill_value=0)
)
for pos in ["GK", "DEF", "MID", "FWD"]:
    if pos not in depth.columns:
        depth[pos] = 0
depth = depth[["GK", "DEF", "MID", "FWD"]]
depth["Total"] = depth.sum(axis=1)
depth = depth.sort_values("Total", ascending=False).drop(columns=["Total"])

fig = px.imshow(
    depth,
    title="Squad depth by position (number of players)",
    labels={"x": "Position", "y": "", "color": "Players"},
    color_continuous_scale="Greens",
    aspect="auto",
    text_auto=True,
)
fig.update_layout(height=900)
st.plotly_chart(fig, use_container_width=True)
