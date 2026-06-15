"""
Tournament Overview — landing page.

Shows:
  - All 12 group standings (live, updates from completed fixtures)
  - Full fixture schedule grouped by date
  - Clickable team names → Team Page
  - Clickable fixtures → Match Centre (placeholder until model is ready)
  - Today's matches highlighted
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
import pandas as pd
from datetime import date

from dashboard.utils import (
    load_fixtures, load_team_features,
    compute_standings, GROUPS, CONF_COLORS, TEAM_TO_GROUP,
)

st.set_page_config(
    page_title="WC 2026 — Tournament Overview",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Sidebar navigation ────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/en/thumb/5/5c/2026_FIFA_World_Cup_emblem.svg/200px-2026_FIFA_World_Cup_emblem.svg.png", width=120)
    st.title("WC 2026")
    st.page_link("pages/01_tournament_overview.py", label="🏆 Tournament Overview", )
    st.page_link("pages/05_player_analytics.py",   label="👤 Player Analytics")
    st.divider()
    st.caption("Match Centre and other pages available after model training.")

# ── Header ────────────────────────────────────────────────────────────────────
st.title("⚽ FIFA World Cup 2026")
st.caption("USA · Canada · Mexico  |  June 11 – July 19, 2026")

# ── Load data ────────────────────────────────────────────────────────────────
fixtures  = load_fixtures()
features  = load_team_features()
standings = compute_standings(fixtures)

today     = pd.Timestamp(date.today())
today_str = today.strftime("%-d %B %Y")

# Confederation lookup
from ingestion.team_name_map import WC2026_TEAMS  # noqa
conf_map = WC2026_TEAMS

# ── Tabs: Groups / Fixtures ───────────────────────────────────────────────────
tab_groups, tab_fixtures = st.tabs(["🗂 Groups & Standings", "📅 All Fixtures"])


# ════════════════════════════════════════════════════════════════════════════
# TAB 1: Groups & Standings
# ════════════════════════════════════════════════════════════════════════════
with tab_groups:

    def _team_button(team: str, key_suffix: str = "") -> None:
        """Render a team button that navigates to the team page."""
        conf = conf_map.get(team, "")
        color = CONF_COLORS.get(conf, "#555555")
        # Use a small HTML badge + button pattern via columns
        if st.button(
            team,
            key=f"btn_{team}_{key_suffix}",
            use_container_width=True,
            type="secondary",
        ):
            st.session_state["selected_team"] = team
            st.switch_page("pages/04_team_page.py")

    # 4 columns × 3 rows = 12 groups
    group_names = list(GROUPS.keys())
    for row_start in range(0, 12, 4):
        cols = st.columns(4, gap="medium")
        for col_idx, grp in enumerate(group_names[row_start:row_start + 4]):
            with cols[col_idx]:
                st.markdown(f"### {grp}")
                stand_df = standings[grp]

                # Standings table with coloured team buttons
                for _, row in stand_df.iterrows():
                    team = row["Team"]
                    conf = conf_map.get(team, "")
                    color = CONF_COLORS.get(conf, "#888")

                    btn_col, pts_col, rec_col = st.columns([3, 1, 2])
                    with btn_col:
                        if st.button(
                            f"{'🟢' if row['#'] <= 2 else '⚪'} {team}",
                            key=f"grp_{grp}_{team}",
                            use_container_width=True,
                            type="secondary",
                        ):
                            st.session_state["selected_team"] = team
                            st.switch_page("pages/04_team_page.py")
                    with pts_col:
                        st.metric(label="", value=int(row["Pts"]), delta=None)
                    with rec_col:
                        st.caption(
                            f"P{int(row['P'])} W{int(row['W'])} "
                            f"D{int(row['D'])} L{int(row['L'])} "
                            f"GD{int(row['GD']):+d}"
                        )

                # Group fixtures (compact)
                grp_fix = fixtures[fixtures["group"] == grp].sort_values("match_date")
                st.divider()
                for _, f in grp_fix.iterrows():
                    is_today = f["match_date"].date() == today.date()
                    is_done  = f["status"] == "completed"

                    score_str = (
                        f"**{int(f['home_score'])}–{int(f['away_score'])}**"
                        if is_done else "vs"
                    )
                    date_str  = f["match_date"].strftime("%d %b")
                    label     = f"{f['home_team']} {score_str} {f['away_team']}"
                    badge     = " 🔴 LIVE" if is_today and not is_done else ""

                    if st.button(
                        f"{date_str}  {f['home_team']} {score_str} {f['away_team']}{badge}",
                        key=f"fix_{f['fixture_id']}",
                        use_container_width=True,
                        type="primary" if is_today else "secondary",
                    ):
                        st.session_state["selected_fixture_id"] = int(f["fixture_id"])
                        st.info("⚙️ Match Centre will be available once the prediction model is trained.", icon="🔮")

        if row_start < 8:
            st.divider()


# ════════════════════════════════════════════════════════════════════════════
# TAB 2: All Fixtures
# ════════════════════════════════════════════════════════════════════════════
with tab_fixtures:

    # Filter controls
    filter_col1, filter_col2, filter_col3 = st.columns([2, 2, 2])
    with filter_col1:
        selected_group = st.selectbox(
            "Filter by group",
            ["All Groups"] + list(GROUPS.keys()),
        )
    with filter_col2:
        status_filter = st.selectbox(
            "Status",
            ["All", "Scheduled", "Completed"],
        )
    with filter_col3:
        date_range = st.date_input(
            "Date range",
            value=(fixtures["match_date"].min().date(),
                   fixtures["match_date"].max().date()),
        )

    # Apply filters
    filt = fixtures.copy()
    if selected_group != "All Groups":
        filt = filt[filt["group"] == selected_group]
    if status_filter == "Scheduled":
        filt = filt[filt["status"] == "scheduled"]
    elif status_filter == "Completed":
        filt = filt[filt["status"] == "completed"]
    if len(date_range) == 2:
        filt = filt[
            (filt["match_date"].dt.date >= date_range[0])
            & (filt["match_date"].dt.date <= date_range[1])
        ]

    st.caption(f"Showing {len(filt)} of {len(fixtures)} fixtures")

    # Group by date
    for match_date, day_fixtures in filt.groupby("match_date"):
        is_today = match_date.date() == today.date()
        date_label = match_date.strftime("%A, %d %B %Y")
        if is_today:
            date_label += "  🔴 TODAY"

        with st.expander(date_label, expanded=is_today or match_date.date() == today.date()):
            for _, f in day_fixtures.iterrows():
                is_done = f["status"] == "completed"
                score_str = (
                    f"{int(f['home_score'])} – {int(f['away_score'])}"
                    if is_done else "vs"
                )

                left, mid, right, venue_col, action_col = st.columns([2.5, 0.8, 2.5, 2.5, 1.5])

                with left:
                    # Home team — clickable
                    if st.button(
                        f"**{f['home_team']}**",
                        key=f"home_{f['fixture_id']}",
                        use_container_width=True,
                        type="secondary",
                    ):
                        st.session_state["selected_team"] = f["home_team"]
                        st.switch_page("pages/04_team_page.py")

                with mid:
                    st.markdown(
                        f"<div style='text-align:center;font-size:1.1rem;font-weight:bold;"
                        f"padding-top:6px;color:{'#28a745' if is_done else '#666'}'>"
                        f"{score_str}</div>",
                        unsafe_allow_html=True,
                    )

                with right:
                    # Away team — clickable
                    if st.button(
                        f"**{f['away_team']}**",
                        key=f"away_{f['fixture_id']}",
                        use_container_width=True,
                        type="secondary",
                    ):
                        st.session_state["selected_team"] = f["away_team"]
                        st.switch_page("pages/04_team_page.py")

                with venue_col:
                    st.caption(f"📍 {f['venue']}  |  {f['group']}")

                with action_col:
                    if st.button(
                        "Match →" if is_done else "Preview →",
                        key=f"mc_{f['fixture_id']}",
                        type="primary" if is_today else "secondary",
                    ):
                        st.session_state["selected_fixture_id"] = int(f["fixture_id"])
                        st.info("⚙️ Match Centre available after model training.", icon="🔮")

            st.divider()

    # Summary metrics
    st.divider()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Fixtures", len(fixtures))
    m2.metric("Completed",      fixtures["status"].eq("completed").sum())
    m3.metric("Scheduled",      fixtures["status"].eq("scheduled").sum())
    m4.metric("Teams",          fixtures[["home_team","away_team"]].stack().nunique())
