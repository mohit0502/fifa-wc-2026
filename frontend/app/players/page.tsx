"use client";

import { useEffect, useState, useMemo } from "react";
import dynamic from "next/dynamic";
import TeamFlag from "@/components/TeamFlag";
import type { PlayerSummary, WcScorer } from "@/lib/types";

const DonutChart = dynamic(() => import("@/components/charts/DonutChart"), { ssr: false });
const HorizontalBar = dynamic(() => import("@/components/charts/HorizontalBar"), { ssr: false });

const POS_COLORS: Record<string, string> = {
  GK:  "#eab308",
  DEF: "#3b82f6",
  MID: "#22c55e",
  FWD: "#ef4444",
};

const CONF_COLORS: Record<string, string> = {
  UEFA:     "#3b82f6",
  CONMEBOL: "#22c55e",
  CONCACAF: "#f97316",
  CAF:      "#f59e0b",
  AFC:      "#ec4899",
  OFC:      "#14b8a6",
};

type Section =
  | "overview"
  | "positions"
  | "age"
  | "clubs"
  | "caps"
  | "scorers"
  | "wc_history";

export default function PlayersPage() {
  const [summary, setSummary] = useState<PlayerSummary | null>(null);
  const [wcScorers, setWcScorers] = useState<WcScorer[]>([]);
  const [confFilter, setConfFilter] = useState("All");
  const [posFilter, setPosFilter] = useState("All");
  const [section, setSection] = useState<Section>("overview");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetch("/data/player_summary.json").then((r) => r.json()),
      fetch("/data/wc_scorers.json").then((r) => r.json()),
    ]).then(([s, wc]) => {
      setSummary(s);
      setWcScorers(wc);
      setLoading(false);
    });
  }, []);

  // Apply filters to top caps / scorers
  const filteredCaps = useMemo(() => {
    if (!summary) return [];
    return summary.top_caps.filter(
      (p) =>
        (confFilter === "All") && // conf filter requires conf field — skip for now
        (posFilter === "All" || p.position === posFilter)
    );
  }, [summary, confFilter, posFilter]);

  const filteredScorers = useMemo(() => {
    if (!summary) return [];
    return summary.top_scorers.filter(
      (p) => posFilter === "All" || p.position === posFilter
    );
  }, [summary, posFilter]);

  // Chart data
  const posDonut = useMemo(() => {
    if (!summary) return [];
    return Object.entries(summary.pos_counts).map(([name, value]) => ({
      name,
      value: value as number,
      color: POS_COLORS[name] ?? "#94a3b8",
    }));
  }, [summary]);

  const topClubsData = useMemo(() => {
    if (!summary) return [];
    return summary.top_clubs.slice(0, 20).map((c) => ({
      label: c.club,
      value: c.count,
    }));
  }, [summary]);

  const topLeaguesData = useMemo(() => {
    if (!summary) return [];
    return summary.top_club_countries.slice(0, 15).map((c) => ({
      label: c.club_country,
      value: c.count,
    }));
  }, [summary]);

  const squadAgeData = useMemo(() => {
    if (!summary) return [];
    return [...summary.squad_age]
      .sort((a, b) => b.avg_age - a.avg_age)
      .slice(0, 30)
      .map((t) => ({ label: t.team_name, value: t.avg_age }));
  }, [summary]);

  const capsData = useMemo(
    () =>
      filteredCaps.slice(0, 25).map((p) => ({
        label: `${p.player_name} (${p.team_name})`,
        value: p.caps,
      })),
    [filteredCaps]
  );

  const scorersData = useMemo(
    () =>
      filteredScorers.slice(0, 25).map((p) => ({
        label: `${p.player_name} (${p.team_name})`,
        value: p.international_goals,
      })),
    [filteredScorers]
  );

  const wcScorersData = useMemo(
    () =>
      wcScorers.slice(0, 25).map((s) => ({
        label: `${s.player_name} (${s.team_name})`,
        value: s.wc_goals,
        color: "#f59e0b",
      })),
    [wcScorers]
  );

  const sections: { key: Section; label: string }[] = [
    { key: "overview",   label: "Overview" },
    { key: "positions",  label: "Positions" },
    { key: "age",        label: "Ages" },
    { key: "clubs",      label: "Clubs" },
    { key: "caps",       label: "Caps" },
    { key: "scorers",    label: "Scorers" },
    { key: "wc_history", label: "WC History" },
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-muted">
        Loading player data…
      </div>
    );
  }
  if (!summary) return <div className="text-muted text-center py-20">No data</div>;

  return (
    <div>
      {/* Page header */}
      <div className="mb-8">
        <h1 className="text-3xl font-extrabold text-text mb-1">Player Analytics</h1>
        <p className="text-muted text-sm">
          {summary.total_players} players · {summary.total_teams} teams · WC 2026 squads
        </p>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-4 mb-8">
        {[
          { label: "Players",       value: summary.total_players.toLocaleString() },
          { label: "Teams",         value: summary.total_teams },
          { label: "Clubs",         value: summary.total_clubs },
          { label: "Avg Age",       value: summary.avg_age.toFixed(1) },
          { label: "Avg Caps",      value: Math.round(summary.avg_caps) },
        ].map((m) => (
          <div key={m.label} className="bg-surface border border-border rounded-xl p-4 text-center">
            <div className="text-2xl font-bold text-accent">{m.value}</div>
            <div className="text-muted text-xs mt-1">{m.label}</div>
          </div>
        ))}
      </div>

      {/* Position filter */}
      <div className="flex flex-wrap gap-3 mb-6">
        <div className="flex gap-1 bg-surface border border-border rounded-lg p-1">
          {["All", "GK", "DEF", "MID", "FWD"].map((p) => (
            <button
              key={p}
              onClick={() => setPosFilter(p)}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                posFilter === p ? "bg-accent text-white" : "text-muted hover:text-text"
              }`}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      {/* Section nav */}
      <div className="flex gap-1 mb-6 bg-surface p-1 rounded-xl border border-border overflow-x-auto">
        {sections.map((s) => (
          <button
            key={s.key}
            onClick={() => setSection(s.key)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors whitespace-nowrap ${
              section === s.key ? "bg-accent text-white" : "text-muted hover:text-text"
            }`}
          >
            {s.label}
          </button>
        ))}
      </div>

      {/* ── Overview ────────────────────────────────────── */}
      {section === "overview" && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Position donut */}
            <div className="bg-surface border border-border rounded-xl p-6">
              <h3 className="font-semibold mb-4">Position Breakdown</h3>
              <DonutChart data={posDonut} />
            </div>

            {/* Confederation × Position table */}
            <div className="bg-surface border border-border rounded-xl p-6">
              <h3 className="font-semibold mb-4">Confederation × Position</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="text-muted border-b border-border">
                      <th className="text-left py-2 pr-3">Conf</th>
                      {["GK", "DEF", "MID", "FWD"].map((p) => (
                        <th key={p} className="py-2 px-3 text-center">{p}</th>
                      ))}
                      <th className="py-2 px-3 text-center text-text font-bold">Total</th>
                    </tr>
                  </thead>
                  <tbody>
                    {["UEFA", "CONMEBOL", "CONCACAF", "CAF", "AFC", "OFC"].map((conf) => {
                      const byPos = summary.conf_pos
                        .filter((r) => r.conf === conf)
                        .reduce<Record<string, number>>((acc, r) => {
                          acc[r.position] = r.count;
                          return acc;
                        }, {});
                      const total = Object.values(byPos).reduce((a, b) => a + b, 0);
                      if (total === 0) return null;
                      return (
                        <tr key={conf} className="border-b border-border/40 hover:bg-surface2">
                          <td
                            className="py-2.5 pr-3 font-semibold text-xs"
                            style={{ color: CONF_COLORS[conf] ?? "#94a3b8" }}
                          >
                            {conf}
                          </td>
                          {["GK", "DEF", "MID", "FWD"].map((p) => (
                            <td key={p} className="py-2.5 px-3 text-center text-muted">
                              {byPos[p] ?? 0}
                            </td>
                          ))}
                          <td className="py-2.5 px-3 text-center text-text font-bold">{total}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Positions ───────────────────────────────────── */}
      {section === "positions" && (
        <div className="bg-surface border border-border rounded-xl p-6">
          <h3 className="font-semibold mb-6">Position Distribution by Confederation</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            {posDonut.map((pos) => (
              <div key={pos.name} className="text-center">
                <div
                  className="text-5xl font-extrabold"
                  style={{ color: pos.color }}
                >
                  {pos.value}
                </div>
                <div className="text-text font-semibold mt-1">{pos.name}</div>
                <div className="text-muted text-sm">
                  {((pos.value / summary.total_players) * 100).toFixed(1)}% of total
                </div>
                <div
                  className="mt-3 h-1.5 rounded-full"
                  style={{
                    background: `linear-gradient(to right, ${pos.color} ${(pos.value / summary.total_players) * 100}%, #1c2d4a ${(pos.value / summary.total_players) * 100}%)`,
                  }}
                />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Ages ─────────────────────────────────────────── */}
      {section === "age" && (
        <div className="bg-surface border border-border rounded-xl p-6">
          <h3 className="font-semibold mb-4">Average Squad Age by Team</h3>
          <HorizontalBar
            data={squadAgeData}
            valueLabel="Avg Age"
            height={Math.max(400, squadAgeData.length * 22)}
            color="#3b82f6"
          />
        </div>
      )}

      {/* ── Clubs ─────────────────────────────────────────── */}
      {section === "clubs" && (
        <div className="space-y-6">
          <div className="bg-surface border border-border rounded-xl p-6">
            <h3 className="font-semibold mb-4">Top 20 Clubs (by players sent)</h3>
            <HorizontalBar data={topClubsData} valueLabel="Players" height={520} color="#3b82f6" />
          </div>
          <div className="bg-surface border border-border rounded-xl p-6">
            <h3 className="font-semibold mb-4">Top Leagues (by club country)</h3>
            <HorizontalBar data={topLeaguesData} valueLabel="Players" height={400} color="#14b8a6" />
          </div>
        </div>
      )}

      {/* ── Caps ──────────────────────────────────────────── */}
      {section === "caps" && (
        <div className="space-y-6">
          <div className="bg-surface border border-border rounded-xl p-6">
            <h3 className="font-semibold mb-4">Most Experienced Players (Caps) · Top 25</h3>
            <HorizontalBar data={capsData} valueLabel="Caps" height={640} color="#a855f7" />
          </div>
          {/* Table */}
          <div className="bg-surface border border-border rounded-xl p-6">
            <h3 className="font-semibold mb-4">Caps Leaderboard</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-muted border-b border-border text-left">
                    <th className="py-2 pr-3">#</th>
                    <th className="py-2 pr-4">Player</th>
                    <th className="py-2 pr-4">Team</th>
                    <th className="py-2 pr-3">Pos</th>
                    <th className="py-2 pr-3 text-center">Age</th>
                    <th className="py-2 pr-3 text-center">Caps</th>
                    <th className="py-2 text-center">Goals</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredCaps.slice(0, 30).map((p, i) => (
                    <tr key={i} className="border-b border-border/40 hover:bg-surface2 transition-colors">
                      <td className="py-2.5 pr-3 text-muted">{i + 1}</td>
                      <td className="py-2.5 pr-4 font-medium text-text">{p.player_name}</td>
                      <td className="py-2.5 pr-4">
                        <TeamFlag name={p.team_name} size="sm" />
                      </td>
                      <td className="py-2.5 pr-3">
                        <span
                          className="text-xs px-2 py-0.5 rounded-full font-bold"
                          style={{ background: `${POS_COLORS[p.position] ?? "#64748b"}33`, color: POS_COLORS[p.position] ?? "#94a3b8" }}
                        >
                          {p.position}
                        </span>
                      </td>
                      <td className="py-2.5 pr-3 text-center text-muted">{p.age ?? "–"}</td>
                      <td className="py-2.5 pr-3 text-center font-bold text-accent">{p.caps}</td>
                      <td className="py-2.5 text-center text-gold">{p.international_goals || "–"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ── Scorers ───────────────────────────────────────── */}
      {section === "scorers" && (
        <div className="space-y-6">
          <div className="bg-surface border border-border rounded-xl p-6">
            <h3 className="font-semibold mb-4">International Goals Leaders · Top 25</h3>
            <HorizontalBar data={scorersData} valueLabel="Goals" height={640} color="#ef4444" />
          </div>
          <div className="bg-surface border border-border rounded-xl p-6">
            <h3 className="font-semibold mb-4">International Goals Leaderboard</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-muted border-b border-border text-left">
                    <th className="py-2 pr-3">#</th>
                    <th className="py-2 pr-4">Player</th>
                    <th className="py-2 pr-4">Team</th>
                    <th className="py-2 pr-3">Pos</th>
                    <th className="py-2 pr-3 text-center">Caps</th>
                    <th className="py-2 text-center">Goals</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredScorers.slice(0, 30).map((p, i) => (
                    <tr key={i} className="border-b border-border/40 hover:bg-surface2 transition-colors">
                      <td className="py-2.5 pr-3 text-muted">{i + 1}</td>
                      <td className="py-2.5 pr-4 font-medium text-text">{p.player_name}</td>
                      <td className="py-2.5 pr-4">
                        <TeamFlag name={p.team_name} size="sm" />
                      </td>
                      <td className="py-2.5 pr-3">
                        <span
                          className="text-xs px-2 py-0.5 rounded-full font-bold"
                          style={{ background: `${POS_COLORS[p.position] ?? "#64748b"}33`, color: POS_COLORS[p.position] ?? "#94a3b8" }}
                        >
                          {p.position}
                        </span>
                      </td>
                      <td className="py-2.5 pr-3 text-center text-muted">{p.caps ?? "–"}</td>
                      <td className="py-2.5 text-center font-bold text-gold text-lg">{p.international_goals}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ── WC History ─────────────────────────────────────── */}
      {section === "wc_history" && (
        <div className="space-y-6">
          <div className="bg-surface border border-border rounded-xl p-6">
            <h3 className="font-semibold mb-2">All-Time World Cup Top Scorers (1930–2022)</h3>
            <p className="text-muted text-sm mb-4">Source: Fjelstul World Cup Database</p>
            {wcScorers.length === 0 ? (
              <p className="text-muted">No data available</p>
            ) : (
              <HorizontalBar data={wcScorersData} valueLabel="WC Goals" height={640} color="#f59e0b" />
            )}
          </div>

          {/* WC scorers table */}
          {wcScorers.length > 0 && (
            <div className="bg-surface border border-border rounded-xl p-6">
              <h3 className="font-semibold mb-4">All-Time WC Scorers Table</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-muted border-b border-border text-left">
                      <th className="py-2 pr-3">#</th>
                      <th className="py-2 pr-4">Player</th>
                      <th className="py-2 pr-4">Country</th>
                      <th className="py-2 text-center">WC Goals</th>
                    </tr>
                  </thead>
                  <tbody>
                    {wcScorers.slice(0, 30).map((s, i) => (
                      <tr key={i} className="border-b border-border/40 hover:bg-surface2 transition-colors">
                        <td className="py-2.5 pr-3 text-muted font-bold">
                          {i + 1 <= 3 ? ["🥇","🥈","🥉"][i] : i + 1}
                        </td>
                        <td className="py-2.5 pr-4 font-medium text-text">{s.player_name}</td>
                        <td className="py-2.5 pr-4 text-muted">{s.team_name}</td>
                        <td className="py-2.5 text-center font-bold text-gold text-lg">{s.wc_goals}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
