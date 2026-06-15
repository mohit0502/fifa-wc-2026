"use client";

import { useEffect, useState, useMemo } from "react";
import Link from "next/link";
import TeamFlag from "@/components/TeamFlag";
import GroupBadge from "@/components/GroupBadge";
import { GROUP_COLORS, GROUPS_ORDER, GROUP_TEAMS, computeStandings } from "@/lib/groups";
import { slugify } from "@/lib/slugify";
import type { Fixture, GroupInfo, StandingRow } from "@/lib/types";

type Tab = "groups" | "fixtures";
type FixtureFilter = "all" | "scheduled" | "completed";

export default function TournamentPage() {
  const [fixtures, setFixtures] = useState<Fixture[]>([]);
  const [groups, setGroups] = useState<Record<string, GroupInfo>>({});
  const [tab, setTab] = useState<Tab>("groups");
  const [groupFilter, setGroupFilter] = useState("All");
  const [statusFilter, setStatusFilter] = useState<FixtureFilter>("all");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetch("/data/fixtures.json").then((r) => r.json()),
      fetch("/data/groups.json").then((r) => r.json()),
    ]).then(([f, g]) => {
      setFixtures(f);
      setGroups(g);
      setLoading(false);
    });
  }, []);

  const today = new Date().toISOString().slice(0, 10);

  // Standings computed from fixtures
  const standings = useMemo(() => {
    const out: Record<string, StandingRow[]> = {};
    for (const grpName of GROUPS_ORDER) {
      const letter = grpName.split(" ")[1];
      const teams = groups[letter]?.teams.map((t) => t.name) ?? GROUP_TEAMS[grpName];
      if (teams) out[grpName] = computeStandings(fixtures, grpName, teams);
    }
    return out;
  }, [fixtures, groups]);

  // Filtered fixtures
  const filteredFixtures = useMemo(() => {
    return fixtures
      .filter((f) => groupFilter === "All" || f.group === groupFilter)
      .filter((f) =>
        statusFilter === "all" ? true :
        statusFilter === "scheduled" ? f.status === "scheduled" :
        f.status === "completed"
      );
  }, [fixtures, groupFilter, statusFilter]);

  // Group fixtures by date
  const byDate = useMemo(() => {
    const map: Record<string, Fixture[]> = {};
    for (const f of filteredFixtures) {
      const d = f.match_date?.slice(0, 10) ?? "TBD";
      (map[d] ??= []).push(f);
    }
    return Object.entries(map).sort(([a], [b]) => a.localeCompare(b));
  }, [filteredFixtures]);

  const completed = fixtures.filter((f) => f.status === "completed").length;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-muted">
        Loading tournament data…
      </div>
    );
  }

  return (
    <div>
      {/* Hero */}
      <div className="mb-8 text-center py-8 relative overflow-hidden rounded-2xl bg-surface border border-border">
        <div className="absolute inset-0 bg-gradient-to-br from-accent/5 to-gold/5 pointer-events-none" />
        <p className="text-muted text-sm uppercase tracking-widest mb-2">USA · Canada · Mexico</p>
        <h1 className="text-4xl md:text-5xl font-extrabold text-text mb-2">
          <span className="text-gold">FIFA</span> World Cup 2026
        </h1>
        <p className="text-muted text-sm">11 June – 19 July 2026</p>
        <div className="flex justify-center gap-8 mt-6">
          {[
            { label: "Teams", value: "48" },
            { label: "Fixtures", value: String(fixtures.length) },
            { label: "Completed", value: String(completed) },
            { label: "Groups", value: "12" },
          ].map((m) => (
            <div key={m.label} className="text-center">
              <div className="text-2xl font-bold text-accent">{m.value}</div>
              <div className="text-xs text-muted mt-0.5">{m.label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Tab nav */}
      <div className="flex gap-1 mb-6 bg-surface p-1 rounded-xl border border-border w-fit">
        {(["groups", "fixtures"] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-5 py-2 rounded-lg text-sm font-medium transition-colors capitalize ${
              tab === t
                ? "bg-accent text-white"
                : "text-muted hover:text-text"
            }`}
          >
            {t === "groups" ? "🗂 Groups & Standings" : "📅 All Fixtures"}
          </button>
        ))}
      </div>

      {/* ── Groups tab ───────────────────────────────────── */}
      {tab === "groups" && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {GROUPS_ORDER.map((grpName) => {
            const letter = grpName.split(" ")[1];
            const color = GROUP_COLORS[letter];
            const rows = standings[grpName] ?? [];
            const grpFixtures = fixtures
              .filter((f) => f.group === grpName)
              .sort((a, b) => a.match_date.localeCompare(b.match_date));

            return (
              <div
                key={grpName}
                className="bg-surface border border-border rounded-xl overflow-hidden flex flex-col"
                style={{ borderTopColor: color, borderTopWidth: 3 }}
              >
                {/* Group header */}
                <div className="px-4 py-3 flex items-center justify-between">
                  <GroupBadge group={grpName} />
                  <span className="text-muted text-xs">
                    {grpFixtures.filter((f) => f.status === "completed").length}/
                    {grpFixtures.length} played
                  </span>
                </div>

                {/* Standings */}
                <div className="px-2 pb-2">
                  <table className="w-full text-xs table-fixed">
                    <colgroup>
                      <col style={{ width: 18 }} />  {/* # */}
                      <col />                         {/* Team — flex remaining */}
                      <col style={{ width: 20 }} />  {/* P */}
                      <col style={{ width: 20 }} />  {/* W */}
                      <col style={{ width: 20 }} />  {/* D */}
                      <col style={{ width: 20 }} />  {/* L */}
                      <col style={{ width: 26 }} />  {/* GD */}
                      <col style={{ width: 26 }} />  {/* Pts */}
                    </colgroup>
                    <thead>
                      <tr className="text-muted">
                        <th className="text-left pl-2 py-1">#</th>
                        <th className="text-left pl-1 py-1">Team</th>
                        <th className="py-1 text-center">P</th>
                        <th className="py-1 text-center">W</th>
                        <th className="py-1 text-center">D</th>
                        <th className="py-1 text-center">L</th>
                        <th className="py-1 text-center">GD</th>
                        <th className="py-1 text-center font-bold">Pts</th>
                      </tr>
                    </thead>
                    <tbody>
                      {rows.map((row, i) => (
                        <tr
                          key={row.team}
                          className={`${
                            i < 2 ? "border-l-2" : ""
                          } hover:bg-surface2 transition-colors`}
                          style={i < 2 ? { borderLeftColor: color } : {}}
                        >
                          <td className="pl-2 py-1.5 text-muted">{i + 1}</td>
                          <td className="pl-1 py-1.5 overflow-hidden">
                            <TeamFlag name={row.team} size="sm" truncate />
                          </td>
                          <td className="py-1.5 text-center text-muted">{row.P}</td>
                          <td className="py-1.5 text-center text-muted">{row.W}</td>
                          <td className="py-1.5 text-center text-muted">{row.D}</td>
                          <td className="py-1.5 text-center text-muted">{row.L}</td>
                          <td className="py-1.5 text-center text-muted">
                            {row.GD > 0 ? `+${row.GD}` : row.GD}
                          </td>
                          <td className="py-1.5 text-center font-bold text-text">{row.Pts}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Group fixtures */}
                <div className="border-t border-border mt-auto">
                  {grpFixtures.map((f) => {
                    const isToday = f.match_date?.slice(0, 10) === today;
                    const done = f.status === "completed";
                    return (
                      <div
                        key={f.fixture_id}
                        className={`px-3 py-2 text-xs border-b border-border/50 last:border-0 ${
                          isToday ? "bg-accent/5" : ""
                        }`}
                      >
                        <div className="flex items-center justify-between gap-1">
                          <span className="text-muted shrink-0">
                            {new Date(f.match_date + "T12:00:00").toLocaleDateString("en-GB", {
                              day: "numeric",
                              month: "short",
                            })}
                          </span>
                          <div className="flex items-center gap-1 flex-1 justify-center overflow-hidden">
                            <Link
                              href={`/team/${slugify(f.home_team)}`}
                              className="text-text hover:text-accent truncate text-right flex-1"
                            >
                              {f.home_team}
                            </Link>
                            <span
                              className={`shrink-0 px-1.5 font-mono font-bold rounded ${
                                done ? "text-gold" : "text-muted"
                              }`}
                            >
                              {done
                                ? `${f.home_score}–${f.away_score}`
                                : isToday
                                ? "🔴"
                                : "vs"}
                            </span>
                            <Link
                              href={`/team/${slugify(f.away_team)}`}
                              className="text-text hover:text-accent truncate flex-1"
                            >
                              {f.away_team}
                            </Link>
                          </div>
                          <Link
                            href={`/match/${f.fixture_id}`}
                            className="text-muted hover:text-accent shrink-0 ml-1"
                            title="Match Centre"
                          >
                            →
                          </Link>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* ── Fixtures tab ───────────────────────────────── */}
      {tab === "fixtures" && (
        <div>
          {/* Filters */}
          <div className="flex flex-wrap gap-3 mb-6">
            <select
              className="bg-surface border border-border rounded-lg px-3 py-2 text-sm text-text focus:outline-none focus:border-accent"
              value={groupFilter}
              onChange={(e) => setGroupFilter(e.target.value)}
            >
              <option value="All">All Groups</option>
              {GROUPS_ORDER.map((g) => (
                <option key={g} value={g}>{g}</option>
              ))}
            </select>
            <div className="flex gap-1 bg-surface border border-border rounded-lg p-1">
              {(["all", "scheduled", "completed"] as FixtureFilter[]).map((s) => (
                <button
                  key={s}
                  onClick={() => setStatusFilter(s)}
                  className={`px-3 py-1 rounded-md text-sm capitalize transition-colors ${
                    statusFilter === s
                      ? "bg-accent text-white"
                      : "text-muted hover:text-text"
                  }`}
                >
                  {s}
                </button>
              ))}
            </div>
            <span className="text-muted text-sm self-center">
              {filteredFixtures.length} fixtures
            </span>
          </div>

          {/* Fixtures by date */}
          <div className="space-y-6">
            {byDate.map(([date, dayFixtures]) => {
              const isToday = date === today;
              const label = new Date(date + "T12:00:00").toLocaleDateString("en-GB", {
                weekday: "long", day: "numeric", month: "long", year: "numeric",
              });
              return (
                <div key={date}>
                  <div className={`flex items-center gap-3 mb-3 ${isToday ? "text-gold" : "text-muted"}`}>
                    <span className="text-sm font-semibold">{label}</span>
                    {isToday && (
                      <span className="text-xs bg-gold/20 text-gold px-2 py-0.5 rounded-full font-bold animate-pulse">
                        TODAY
                      </span>
                    )}
                    <div className="flex-1 h-px bg-border" />
                  </div>

                  <div className="space-y-2">
                    {dayFixtures.map((f) => {
                      const done = f.status === "completed";
                      return (
                        <div
                          key={f.fixture_id}
                          className={`bg-surface border border-border rounded-xl px-4 py-3 flex items-center gap-4 ${
                            isToday ? "border-gold/30" : ""
                          }`}
                        >
                          {/* Group badge */}
                          <GroupBadge group={f.group} size="sm" />

                          {/* Home */}
                          <div className="flex-1 flex justify-end">
                            <TeamFlag name={f.home_team} size="sm" />
                          </div>

                          {/* Score / vs */}
                          <div className="w-16 text-center">
                            {done ? (
                              <span className="text-gold font-bold text-lg font-mono">
                                {f.home_score}–{f.away_score}
                              </span>
                            ) : isToday ? (
                              <span className="text-red-400 font-bold text-sm animate-pulse">LIVE</span>
                            ) : (
                              <span className="text-muted font-medium">vs</span>
                            )}
                          </div>

                          {/* Away */}
                          <div className="flex-1">
                            <TeamFlag name={f.away_team} size="sm" />
                          </div>

                          {/* Venue */}
                          <div className="hidden md:block text-muted text-xs text-right min-w-0 max-w-40 truncate">
                            {f.venue}
                          </div>

                          {/* Action */}
                          <Link
                            href={`/match/${f.fixture_id}`}
                            className="text-xs px-3 py-1.5 rounded-lg border border-border text-muted hover:border-accent hover:text-accent transition-colors shrink-0"
                          >
                            {done ? "Result →" : "Preview →"}
                          </Link>
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
