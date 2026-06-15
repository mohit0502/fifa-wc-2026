"""
Team Page — one page for all 48 WC 2026 teams.
Team is selected via st.session_state["selected_team"] (set by tournament overview)
or via a dropdown on this page itself.
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
    load_fixtures, load_team_features, load_team_form,
    load_h2h, load_ranking_history, load_goals_dist, load_squads,
    load_fjelstul_matches, CONF_COLORS, RESULT_COLORS, TEAM_TO_GROUP,
)
from ingestion.team_name_map import WC2026_TEAMS

st.set_page_config(
    page_title="WC 2026 — Team",
    page_icon="🏳",
    layout="wide",
    initial_sidebar_state="expanded",
)

ALL_TEAMS = sorted(WC2026_TEAMS.keys())

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("WC 2026")
    st.page_link("pages/01_tournament_overview.py", label="🏆 Tournament Overview")
    st.page_link("pages/05_player_analytics.py",   label="👤 Player Analytics")
    st.divider()
    selected_team = st.selectbox(
        "Select team",
        ALL_TEAMS,
        index=ALL_TEAMS.index(st.session_state.get("selected_team", "England")),
    )
    st.session_state["selected_team"] = selected_team

TEAM = st.session_state["selected_team"]
conf = WC2026_TEAMS.get(TEAM, "")
color = CONF_COLORS.get(conf, "#555")
group = TEAM_TO_GROUP.get(TEAM, "")

# ── Load data ────────────────────────────────────────────────────────────────
features   = load_team_features()
form_df    = load_team_form()
h2h_df     = load_h2h()
rankings   = load_ranking_history()
goals_dist = load_goals_dist()
squads     = load_squads()
fixtures   = load_fixtures()

team_feat  = features[features["team_name"] == TEAM]
team_form  = form_df[form_df["team_name"] == TEAM].sort_values("date", ascending=False)
team_rank  = rankings[rankings["team_name"] == TEAM].sort_values("rank_date")
team_goals = goals_dist[goals_dist["team_name"] == TEAM]
team_squad = squads[squads["team_name"] == TEAM].sort_values(
    ["position", "caps"], ascending=[True, False]
)

# Fixtures for this team
team_fixtures = fixtures[
    (fixtures["home_team"] == TEAM) | (fixtures["away_team"] == TEAM)
].sort_values("match_date")

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    f"<h1 style='color:{color}'>{TEAM}</h1>"
    f"<p style='color:#888;font-size:1rem'>{conf}  ·  {group}</p>",
    unsafe_allow_html=True,
)

# Key metrics row
if not team_feat.empty:
    row = team_feat.iloc[0]
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("FIFA Rank",        f"#{int(row['current_fifa_rank'])}" if pd.notna(row['current_fifa_rank']) else "N/A")
    m2.metric("FIFA Points",      f"{row['current_fifa_points']:.0f}" if pd.notna(row['current_fifa_points']) else "N/A")
    m3.metric("Form Win Rate",    f"{row['form_form_win_rate']:.0%}"  if pd.notna(row['form_form_win_rate']) else "N/A")
    m4.metric("Avg Goals (20gm)", f"{row['avg_goals_scored_20']:.2f}" if pd.notna(row['avg_goals_scored_20']) else "N/A")
    m5.metric("Avg Conceded",     f"{row['avg_goals_conceded_20']:.2f}" if pd.notna(row['avg_goals_conceded_20']) else "N/A")
    m6.metric("WC Appearances",   int(row['wc_appearances_approx']) if pd.notna(row['wc_appearances_approx']) else "N/A")

st.divider()

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_fixtures, tab_form, tab_ranking, tab_h2h, tab_squad, tab_goals = st.tabs([
    "📅 Fixtures", "📊 Form", "📈 FIFA Ranking", "⚔️ H2H", "👥 Squad", "⚽ Goals"
])


# ════════════════════════════════════════════════════════════════════════════
# FIXTURES TAB
# ════════════════════════════════════════════════════════════════════════════
with tab_fixtures:
    st.subheader(f"{TEAM} — Group Stage Fixtures")
    for _, f in team_fixtures.iterrows():
        is_home  = f["home_team"] == TEAM
        opponent = f["away_team"] if is_home else f["home_team"]
        is_done  = f["status"] == "completed"

        if is_done:
            my_score  = int(f["home_score"] if is_home else f["away_score"])
            opp_score = int(f["away_score"] if is_home else f["home_score"])
            result    = "W" if my_score > opp_score else ("D" if my_score == opp_score else "L")
            score_txt = f"{my_score} – {opp_score}"
            badge     = f":{{'W':'green','D':'orange','L':'red'}[result]}[**{result} {score_txt}**]"
        else:
            result    = None
            score_txt = "vs"
            badge     = ":gray[Scheduled]"

        venue_home = "🏠" if is_home else "✈️"
        col_date, col_opp, col_score, col_venue, col_btn = st.columns([1.5, 2.5, 1.2, 2.5, 1.2])
        col_date.write(f["match_date"].strftime("%d %b"))
        col_venue.caption(f"📍 {f['venue']}")

        with col_opp:
            if st.button(
                f"{venue_home} {'vs' if not is_home else ''} {opponent} {'' if is_home else venue_home}",
                key=f"opp_{f['fixture_id']}",
                use_container_width=True,
                type="secondary",
            ):
                st.session_state["selected_team"] = opponent
                st.switch_page("pages/04_team_page.py")

        with col_score:
            if result:
                col_score.markdown(
                    f"<span style='color:{RESULT_COLORS[result]};font-weight:bold'>"
                    f"{result} {score_txt}</span>",
                    unsafe_allow_html=True,
                )
            else:
                col_score.caption("Upcoming")

        with col_btn:
            if st.button("Match →", key=f"mc_team_{f['fixture_id']}", type="secondary"):
                st.session_state["selected_fixture_id"] = int(f["fixture_id"])
                st.info("⚙️ Match Centre available after model training.", icon="🔮")


# ════════════════════════════════════════════════════════════════════════════
# FORM TAB
# ════════════════════════════════════════════════════════════════════════════
with tab_form:
    st.subheader(f"Last {len(team_form)} results")
    if team_form.empty:
        st.info("No form data available.")
    else:
        # Form strip
        form_strip_cols = st.columns(min(len(team_form), 10))
        for i, (_, row) in enumerate(team_form.head(10).iterrows()):
            with form_strip_cols[i]:
                r = row["result"]
                st.markdown(
                    f"<div style='background:{RESULT_COLORS[r]};color:white;"
                    f"text-align:center;border-radius:4px;padding:6px 0;"
                    f"font-weight:bold;font-size:1rem'>{r}</div>"
                    f"<div style='text-align:center;font-size:0.7rem;color:#666;"
                    f"margin-top:2px'>{row['goals_for']}–{row['goals_against']}</div>"
                    f"<div style='text-align:center;font-size:0.65rem;color:#888'>"
                    f"{row['date'].strftime('%d %b')}</div>",
                    unsafe_allow_html=True,
                )

        st.divider()

        # Form table
        disp = team_form[["date","opponent","venue","goals_for","goals_against","result","tournament"]].copy()
        disp["date"] = disp["date"].dt.strftime("%d %b %Y")

        def _style_result(val):
            return f"background-color:{RESULT_COLORS.get(val,'')}22;color:{RESULT_COLORS.get(val,'#000')};font-weight:bold"

        st.dataframe(
            disp.style.applymap(_style_result, subset=["result"]),
            use_container_width=True,
            hide_index=True,
        )

        # W/D/L bar
        counts = team_form["result"].value_counts().reindex(["W","D","L"], fill_value=0)
        fig = go.Figure(go.Bar(
            x=counts.values, y=counts.index, orientation="h",
            marker_color=[RESULT_COLORS[r] for r in counts.index],
            text=counts.values, textposition="inside",
        ))
        fig.update_layout(title="Form summary (last 10)",
                          template="plotly_white", height=200, showlegend=False,
                          margin=dict(l=0, r=0, t=40, b=0))
        st.plotly_chart(fig, use_container_width=True)


# ════════════════════════════════════════════════════════════════════════════
# RANKING TAB
# ════════════════════════════════════════════════════════════════════════════
with tab_ranking:
    if team_rank.empty:
        st.info("No FIFA ranking history available.")
    else:
        # Trajectory chart
        fig = px.line(
            team_rank, x="rank_date", y="rank",
            title=f"{TEAM} — FIFA Ranking history",
            labels={"rank_date": "Date", "rank": "FIFA Rank"},
            template="plotly_white",
            color_discrete_sequence=[color],
        )
        fig.update_yaxes(autorange="reversed", title="FIFA Rank (lower = better)")
        fig.update_traces(line_width=2.5)
        fig.update_layout(height=380)
        st.plotly_chart(fig, use_container_width=True)

        # Points chart
        fig2 = px.line(
            team_rank, x="rank_date", y="total_points",
            title=f"{TEAM} — FIFA Points history",
            labels={"rank_date": "Date", "total_points": "Points"},
            template="plotly_white",
            color_discrete_sequence=[color],
        )
        fig2.update_traces(line_width=2, line_dash="dot")
        fig2.update_layout(height=280)
        st.plotly_chart(fig2, use_container_width=True)

        latest = team_rank.iloc[-1]
        st.caption(
            f"Latest: Rank **{int(latest['rank'])}** · "
            f"Points **{latest['total_points']:.0f}** · "
            f"Change **{int(latest['rank_change']):+d}** · "
            f"As of {latest['rank_date'].strftime('%d %b %Y')}"
        )


# ════════════════════════════════════════════════════════════════════════════
# H2H TAB
# ════════════════════════════════════════════════════════════════════════════
with tab_h2h:
    # Group-stage opponents first, then all WC teams
    group_opponents = [t for t in (GROUPS.get(group, [])) if t != TEAM]
    st.subheader("H2H vs Group Opponents")

    mask_a = h2h_df["team_a"] == TEAM
    mask_b = h2h_df["team_b"] == TEAM

    def _h2h_for_opponent(opp: str) -> pd.Series | None:
        row_a = h2h_df[(h2h_df["team_a"] == TEAM) & (h2h_df["team_b"] == opp)]
        row_b = h2h_df[(h2h_df["team_a"] == opp)  & (h2h_df["team_b"] == TEAM)]
        if not row_a.empty:
            r = row_a.iloc[0]
            return pd.Series({"opponent": opp, "n": r["n_played"],
                               "W": r["a_wins"], "D": r["draws"], "L": r["b_wins"],
                               "GF": r["a_goals"], "GA": r["b_goals"],
                               "last_date": r["last_match_date"], "last_score": r.get("last_score","")})
        elif not row_b.empty:
            r = row_b.iloc[0]
            return pd.Series({"opponent": opp, "n": r["n_played"],
                               "W": r["b_wins"], "D": r["draws"], "L": r["a_wins"],
                               "GF": r["b_goals"], "GA": r["a_goals"],
                               "last_date": r["last_match_date"], "last_score": r.get("last_score","")})
        return None

    for opp in group_opponents:
        h = _h2h_for_opponent(opp)
        if h is not None and int(h["n"]) > 0:
            c1, c2, c3 = st.columns([3, 4, 3])
            with c1:
                if st.button(opp, key=f"h2h_opp_{opp}", use_container_width=True, type="secondary"):
                    st.session_state["selected_team"] = opp
                    st.switch_page("pages/04_team_page.py")
            with c2:
                total = int(h["n"])
                wins, draws, losses = int(h["W"]), int(h["D"]), int(h["L"])
                fig = go.Figure(go.Bar(
                    x=[wins, draws, losses],
                    y=[""],
                    orientation="h",
                    marker_color=["#28a745", "#ffc107", "#dc3545"],
                    text=[f"W{wins}", f"D{draws}", f"L{losses}"],
                    textposition="inside",
                ))
                fig.update_layout(
                    height=60, margin=dict(l=0,r=0,t=0,b=0),
                    showlegend=False, template="plotly_white",
                    barmode="stack", xaxis=dict(showticklabels=False),
                    yaxis=dict(showticklabels=False),
                )
                st.plotly_chart(fig, use_container_width=True)
            with c3:
                st.caption(
                    f"{total} games · GF {int(h['GF'])} GA {int(h['GA'])}\n"
                    f"Last: {h['last_score']} ({str(h['last_date'])[:10] if pd.notna(h['last_date']) else 'N/A'})"
                )
        else:
            c1, c2 = st.columns([3, 7])
            with c1:
                if st.button(opp, key=f"h2h_no_{opp}", use_container_width=True, type="secondary"):
                    st.session_state["selected_team"] = opp
                    st.switch_page("pages/04_team_page.py")
            c2.caption("No previous meetings")

    # All WC teams H2H summary
    st.divider()
    st.subheader("H2H vs All WC 2026 Teams")
    all_h2h_rows = []
    for opp in sorted(WC2026_TEAMS.keys()):
        if opp == TEAM:
            continue
        h = _h2h_for_opponent(opp)
        if h is not None:
            all_h2h_rows.append({
                "Opponent": opp, "Played": int(h["n"]), "W": int(h["W"]),
                "D": int(h["D"]), "L": int(h["L"]),
                "GF": int(h["GF"]), "GA": int(h["GA"]),
                "GD": int(h["GF"]) - int(h["GA"]),
                "Win%": f"{int(h['W'])/int(h['n']):.0%}" if int(h["n"]) > 0 else "0%",
            })

    if all_h2h_rows:
        h2h_summary = pd.DataFrame(all_h2h_rows).sort_values("Played", ascending=False)
        st.dataframe(h2h_summary, use_container_width=True, hide_index=True, height=400)


# ════════════════════════════════════════════════════════════════════════════
# SQUAD TAB
# ════════════════════════════════════════════════════════════════════════════
with tab_squad:
    if team_squad.empty:
        st.info("Squad data not available.")
    else:
        st.subheader(f"{TEAM} — 2026 World Cup Squad")

        pos_order = ["GK", "1 GK", "2 DF", "DEF", "3 MF", "MID", "4 FW", "FWD"]
        pos_labels = {
            "1 GK": "Goalkeepers", "2 DF": "Defenders",
            "3 MF": "Midfielders", "4 FW": "Forwards",
        }
        team_squad["pos_sort"] = team_squad["position"].map({
            "GK": "1 GK", "DEF": "2 DF", "MID": "3 MF", "FWD": "4 FW"
        }).fillna("5 Other")

        for pos_key, pos_label in pos_labels.items():
            pos_players = team_squad[team_squad["pos_sort"] == pos_key]
            if pos_players.empty:
                continue

            st.markdown(f"**{pos_label}**")
            cols = st.columns(min(4, len(pos_players)))
            for i, (_, p) in enumerate(pos_players.iterrows()):
                with cols[i % 4]:
                    age_str  = f"Age {int(p['age'])}" if pd.notna(p["age"]) else ""
                    caps_str = f"{int(p['caps'])}caps" if pd.notna(p["caps"]) else ""
                    goals_str = f"{int(p['international_goals'])}g" if pd.notna(p["international_goals"]) else ""
                    club_str = p["club"] if pd.notna(p["club"]) else ""
                    num_str  = f"#{int(p['squad_number'])}" if pd.notna(p["squad_number"]) else ""

                    st.markdown(
                        f"<div style='border:1px solid #ddd;border-radius:6px;"
                        f"padding:8px 10px;margin-bottom:8px;background:#fafafa'>"
                        f"<div style='font-weight:600;font-size:0.9rem'>{num_str} {p['player_name']}</div>"
                        f"<div style='font-size:0.75rem;color:#666'>{club_str}</div>"
                        f"<div style='font-size:0.72rem;color:#888;margin-top:2px'>"
                        f"{age_str}  ·  {caps_str}  ·  {goals_str}</div>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
            st.divider()


# ════════════════════════════════════════════════════════════════════════════
# GOALS TAB
# ════════════════════════════════════════════════════════════════════════════
with tab_goals:
    if team_goals.empty:
        st.info("No goals data available.")
    else:
        recent_goals = team_goals[team_goals["date"].dt.year >= 2010].copy()

        # Goals scored & conceded distributions
        col1, col2 = st.columns(2)
        with col1:
            fig = px.histogram(
                recent_goals, x="goals_scored", nbins=10,
                title="Goals Scored per Match (2010–present)",
                template="plotly_white",
                color_discrete_sequence=[color],
            )
            fig.update_layout(bargap=0.1, height=300)
            st.plotly_chart(fig, use_container_width=True)
            st.caption(
                f"Mean: **{recent_goals['goals_scored'].mean():.2f}**  ·  "
                f"Clean sheets (0 GA): **{(recent_goals['goals_conceded']==0).mean():.0%}**"
            )
        with col2:
            fig2 = px.histogram(
                recent_goals, x="goals_conceded", nbins=10,
                title="Goals Conceded per Match (2010–present)",
                template="plotly_white",
                color_discrete_sequence=["#dc3545"],
            )
            fig2.update_layout(bargap=0.1, height=300)
            st.plotly_chart(fig2, use_container_width=True)
            st.caption(
                f"Mean: **{recent_goals['goals_conceded'].mean():.2f}**  ·  "
                f"0-goal hauls: **{(recent_goals['goals_scored']==0).mean():.0%}**"
            )

        # Rolling average timeline
        ts = (
            recent_goals.set_index("date")
            .sort_index()[["goals_scored","goals_conceded"]]
            .rolling("365D").mean()
            .reset_index()
        )
        fig3 = px.line(
            ts, x="date", y=["goals_scored","goals_conceded"],
            title="Rolling 12-month avg goals (scored vs conceded)",
            template="plotly_white",
            color_discrete_map={"goals_scored": color, "goals_conceded": "#dc3545"},
            labels={"value": "Goals/match", "date": ""},
        )
        fig3.update_layout(legend_title="", height=320)
        st.plotly_chart(fig3, use_container_width=True)
