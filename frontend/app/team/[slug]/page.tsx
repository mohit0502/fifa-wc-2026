"use client";

import { useEffect, useState, useMemo } from "react";
import { useParams } from "next/navigation";
import dynamic from "next/dynamic";
import TeamFlag from "@/components/TeamFlag";
import GroupBadge from "@/components/GroupBadge";
import { getFlagUrl } from "@/lib/flags";
import { CONF_COLORS, GROUP_TEAMS, computeStandings } from "@/lib/groups";
import type {
  Squad, FormEntry, RankingEntry, H2HRecord,
  TeamFeatures, Fixture, StandingRow,
} from "@/lib/types";

const RankingChart = dynamic(() => import("@/components/charts/RankingChart"), { ssr: false });
const PitchXI      = dynamic(() => import("@/components/PitchXI"), { ssr: false });

type LineupPlayer = { pos: string; name: string; short_name: string; injury: string | null };
type SquadPlayer = {
  squad_number: number | null; position: string | null; player_name: string;
  date_of_birth: string | null; age: number | null; caps: number | null;
  international_goals: number | null; club: string | null; club_country: string | null;
};

function normalizeName(n: string): string {
  return n.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/[^a-z0-9 ]/g, "").trim();
}

type Tab = "lineup" | "form" | "ranking" | "squad" | "h2h";

const RESULT_COLOR: Record<string, string> = {
  W: "bg-green-500/20 text-green-400 border border-green-500/30",
  D: "bg-yellow-500/20 text-yellow-400 border border-yellow-500/30",
  L: "bg-red-500/20 text-red-400 border border-red-500/30",
};
const POS_COLOR: Record<string, string> = {
  GK:  "bg-yellow-500/20 text-yellow-300",
  DEF: "bg-blue-500/20 text-blue-300",
  MID: "bg-green-500/20 text-green-300",
  FWD: "bg-red-500/20 text-red-300",
};

export default function TeamPage() {
  const { slug } = useParams() as { slug: string };
  const [squad, setSquad] = useState<Squad | null>(null);
  const [form, setForm] = useState<FormEntry[]>([]);
  const [rankings, setRankings] = useState<RankingEntry[]>([]);
  const [h2hAll, setH2hAll] = useState<H2HRecord[]>([]);
  const [features, setFeatures] = useState<TeamFeatures | null>(null);
  const [fixtures, setFixtures] = useState<Fixture[]>([]);
  const [lineup, setLineup] = useState<{
    status: string; formation: string; scraped_at?: string;
    players: Array<{ pos: string; name: string; short_name: string; injury: string | null }>;
    injuries: Array<{ pos: string; name: string; short_name: string; injury: string | null }>;
  } | null>(null);
  const [tab, setTab] = useState<Tab>("lineup");
  const [posFilter, setPosFilter] = useState("All");
  const [selectedPlayer, setSelectedPlayer] = useState<{ lineup: LineupPlayer; squad: SquadPlayer | null } | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetch("/data/squads.json").then((r) => r.json()),
      fetch("/data/form.json").then((r) => r.json()),
      fetch("/data/rankings.json").then((r) => r.json()),
      fetch("/data/h2h.json").then((r) => r.json()),
      fetch("/data/team_features.json").then((r) => r.json()),
      fetch("/data/fixtures.json").then((r) => r.json()),
      fetch("/data/lineups.json").then((r) => r.json()),
    ]).then(([squads, formMap, rankMap, h2h, feats, fix, lineups]) => {
      setSquad(squads[slug] ?? null);
      setForm(formMap[slug] ?? []);
      setRankings(rankMap[slug] ?? []);
      setH2hAll(h2h);
      setFeatures(feats[slug] ?? null);
      setFixtures(fix);
      setLineup(lineups[slug] ?? null);
      setLoading(false);
    });
  }, [slug]);

  const teamName = squad?.team_name ?? "";
  const group = squad?.group ?? features?.group ?? "";
  const conf = squad?.conf ?? features?.conf ?? "";

  // Group standings
  const groupStandings: StandingRow[] = useMemo(() => {
    if (!group) return [];
    const teams = GROUP_TEAMS[group];
    return teams ? computeStandings(fixtures, group, teams) : [];
  }, [fixtures, group]);

  // H2H vs group opponents
  const groupOpponents = useMemo(() => {
    if (!group) return [];
    return (GROUP_TEAMS[group] ?? []).filter((t) => t !== teamName);
  }, [group, teamName]);

  const h2hRecords = useMemo(() => {
    return h2hAll.filter(
      (r) =>
        (r.team_a === teamName || r.team_b === teamName) &&
        groupOpponents.includes(r.team_a === teamName ? r.team_b : r.team_a)
    );
  }, [h2hAll, teamName, groupOpponents]);

  // Squad filter
  const filteredSquad = useMemo(() => {
    if (!squad) return [];
    if (posFilter === "All") return squad.players;
    return squad.players.filter((p) => p.position === posFilter);
  }, [squad, posFilter]);

  // Name-normalized lookup: lineup player name → squad player
  const squadLookup = useMemo(() => {
    const map = new Map<string, SquadPlayer>();
    if (!squad) return map;
    for (const p of squad.players) {
      const norm = normalizeName(p.player_name);
      map.set(norm, p);
      const parts = norm.split(" ");
      const last = parts[parts.length - 1];
      if (!map.has(last)) map.set(last, p);
    }
    return map;
  }, [squad]);

  function findSquadPlayer(lineupName: string): SquadPlayer | null {
    const norm = normalizeName(lineupName);
    if (squadLookup.has(norm)) return squadLookup.get(norm)!;
    const parts = norm.split(" ");
    return squadLookup.get(parts[parts.length - 1]) ?? null;
  }

  function handlePlayerClick(p: LineupPlayer) {
    setSelectedPlayer({ lineup: p, squad: findSquadPlayer(p.name) });
  }

  const flagUrl = getFlagUrl(teamName, 160);
  const confColor = CONF_COLORS[conf] ?? "#64748b";

  const tabs: { key: Tab; label: string }[] = [
    { key: "lineup",  label: "🟢 Predicted XI" },
    { key: "form",    label: "📋 Form" },
    { key: "ranking", label: "📈 Ranking" },
    { key: "squad",   label: "👤 Squad" },
    { key: "h2h",     label: "⚔️ vs Group" },
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-muted">
        Loading team data…
      </div>
    );
  }

  if (!squad && !features) {
    return (
      <div className="text-center py-20 text-muted">
        Team not found. <a href="/" className="text-accent hover:underline">Return home</a>
      </div>
    );
  }

  const rank = features?.fifa_rank;

  return (
    <div>
      {/* Hero */}
      <div className="relative overflow-hidden rounded-2xl bg-surface border border-border mb-8">
        <div className="absolute inset-0 bg-gradient-to-br from-accent/5 via-transparent to-gold/5 pointer-events-none" />
        {/* Large bg flag (faint) */}
        {flagUrl && (
          <div
            className="absolute right-0 top-0 bottom-0 w-72 opacity-[0.08] pointer-events-none"
            style={{
              backgroundImage: `url(${flagUrl})`,
              backgroundSize: "cover",
              backgroundPosition: "center",
            }}
          />
        )}
        <div className="relative p-6 md:p-10 flex flex-col md:flex-row items-start md:items-center gap-6">
          {/* Flag */}
          {flagUrl && (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={flagUrl}
              alt={teamName}
              className="w-24 md:w-32 rounded-xl shadow-lg border border-border/50 object-cover"
            />
          )}
          <div className="flex-1">
            <div className="flex flex-wrap items-center gap-3 mb-2">
              <GroupBadge group={group} />
              <span
                className="text-xs px-2 py-1 rounded-full font-medium"
                style={{ background: `${confColor}22`, color: confColor, border: `1px solid ${confColor}44` }}
              >
                {conf}
              </span>
            </div>
            <h1 className="text-3xl md:text-4xl font-extrabold text-text mb-3">{teamName}</h1>
            <div className="flex flex-wrap gap-6 text-sm">
              {rank && (
                <div>
                  <span className="text-muted">FIFA Rank </span>
                  <span className="text-accent font-bold text-lg">#{rank}</span>
                </div>
              )}
              {features?.wc_appearances_approx !== undefined && (
                <div>
                  <span className="text-muted">WC Apps </span>
                  <span className="text-text font-bold">{features.wc_appearances_approx}</span>
                </div>
              )}
              {squad && (
                <div>
                  <span className="text-muted">Squad </span>
                  <span className="text-text font-bold">{squad.players.length} players</span>
                </div>
              )}
              {features?.all_time_win_rate != null && (
                <div>
                  <span className="text-muted">All-time Win% </span>
                  <span className="text-text font-bold">
                    {(features.all_time_win_rate * 100).toFixed(0)}%
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* Ranking bubble */}
          {rank && (
            <div className="text-center bg-surface2 border border-border rounded-xl px-6 py-4 shrink-0">
              <div className="text-4xl font-extrabold text-accent">#{rank}</div>
              <div className="text-muted text-xs mt-1">FIFA Ranking</div>
            </div>
          )}
        </div>

        {/* Group standing strip */}
        {groupStandings.length > 0 && (
          <div className="border-t border-border px-6 py-3 flex items-center gap-6 overflow-x-auto">
            <span className="text-muted text-xs shrink-0">Group Standings</span>
            {groupStandings.map((row, i) => (
              <div
                key={row.team}
                className={`flex items-center gap-2 text-xs shrink-0 ${
                  row.team === teamName ? "text-gold" : "text-muted"
                }`}
              >
                <span className="font-bold">{i + 1}.</span>
                <TeamFlag name={row.team} size="sm" showLink={row.team !== teamName} />
                <span className="font-bold">{row.Pts}pts</span>
                <span className="text-muted/60">({row.W}W {row.D}D {row.L}L)</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 bg-surface p-1 rounded-xl border border-border overflow-x-auto">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors whitespace-nowrap ${
              tab === t.key
                ? "bg-accent text-white"
                : "text-muted hover:text-text"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* ── Lineup tab ───────────────────────────────────── */}
      {tab === "lineup" && (
        <div className="bg-surface border border-border rounded-xl p-6">
          <h2 className="text-lg font-semibold mb-5">Predicted Starting XI</h2>
          {!lineup ? (
            <p className="text-muted">No lineup data available for this team.</p>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              {/* Pitch visual */}
              <PitchXI
                players={lineup.players}
                formation={lineup.formation}
                status={lineup.status as "predicted" | "confirmed"}
                onPlayerClick={handlePlayerClick}
                selectedName={selectedPlayer?.lineup.name}
              />

              {/* Player list + injuries */}
              <div>
                <h3 className="text-sm font-semibold text-muted uppercase tracking-wider mb-3">
                  Starting XI · {lineup.formation}
                </h3>
                <div className="space-y-1 mb-6">
                  {lineup.players.map((p, i) => {
                    const isSelected = selectedPlayer?.lineup.name === p.name;
                    return (
                      <div
                        key={i}
                        onClick={() => handlePlayerClick(p)}
                        className={`flex items-center gap-3 px-3 py-2 rounded-lg cursor-pointer transition-colors ${
                          isSelected
                            ? "bg-accent/20 border border-accent/40"
                            : "hover:bg-surface2"
                        }`}
                      >
                        <span className="text-muted text-xs w-4 text-right">{i + 1}</span>
                        <span className="text-xs font-bold px-1.5 py-0.5 rounded bg-surface2 text-muted w-10 text-center shrink-0">
                          {p.pos}
                        </span>
                        <span className={`text-sm flex-1 ${isSelected ? "text-accent font-semibold" : "text-text"}`}>
                          {p.name}
                        </span>
                        {p.injury && (
                          <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${
                            p.injury === "OUT"
                              ? "bg-red-500/20 text-red-400"
                              : "bg-yellow-500/20 text-yellow-400"
                          }`}>
                            {p.injury}
                          </span>
                        )}
                      </div>
                    );
                  })}
                </div>

                {lineup.injuries.length > 0 && (
                  <>
                    <h3 className="text-sm font-semibold text-muted uppercase tracking-wider mb-3">
                      Injury / Suspension List
                    </h3>
                    <div className="space-y-1">
                      {lineup.injuries.map((p, i) => (
                        <div
                          key={i}
                          className="flex items-center gap-3 px-3 py-2 rounded-lg bg-surface2/50"
                        >
                          <span className="text-xs font-bold px-1.5 py-0.5 rounded bg-surface2 text-muted w-10 text-center shrink-0">
                            {p.pos}
                          </span>
                          <span className="text-muted text-sm flex-1">{p.name}</span>
                          {p.injury && (
                            <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${
                              p.injury === "OUT"
                                ? "bg-red-500/20 text-red-400"
                                : "bg-yellow-500/20 text-yellow-400"
                            }`}>
                              {p.injury}
                            </span>
                          )}
                        </div>
                      ))}
                    </div>
                  </>
                )}

                <p className="text-muted text-xs mt-6">
                  Source: RotoWire · Scraped {lineup.scraped_at?.slice(0, 10) ?? "pre-tournament"}
                </p>
              </div>
            </div>
          )}

          {/* Player detail card */}
          {selectedPlayer && (
            <div className="mt-6 relative bg-surface2 border border-accent/40 rounded-xl p-5 flex flex-col sm:flex-row gap-5">
              <button
                onClick={() => setSelectedPlayer(null)}
                className="absolute top-3 right-3 text-muted hover:text-text text-lg leading-none"
                aria-label="Close"
              >
                ×
              </button>

              {/* Position circle */}
              <div className="flex items-start gap-4">
                <div
                  className="w-14 h-14 rounded-full flex items-center justify-center text-sm font-bold text-white shrink-0 border-2 border-white/20"
                  style={{
                    background: selectedPlayer.lineup.injury ? "#991b1b" : "#1d4ed8",
                  }}
                >
                  {selectedPlayer.lineup.pos.slice(0, 3)}
                </div>
                <div>
                  <p className="text-text font-bold text-lg leading-tight">{selectedPlayer.lineup.name}</p>
                  <p className="text-muted text-xs mt-0.5">{selectedPlayer.lineup.pos}</p>
                  {selectedPlayer.lineup.injury && (
                    <span className={`inline-block mt-1 text-xs font-bold px-2 py-0.5 rounded-full ${
                      selectedPlayer.lineup.injury === "OUT"
                        ? "bg-red-500/20 text-red-400"
                        : "bg-yellow-500/20 text-yellow-400"
                    }`}>
                      {selectedPlayer.lineup.injury}
                    </span>
                  )}
                </div>
              </div>

              {/* Stats grid */}
              {selectedPlayer.squad ? (
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-x-8 gap-y-3 text-sm flex-1">
                  {[
                    { label: "Club", value: selectedPlayer.squad.club
                        ? `${selectedPlayer.squad.club}${selectedPlayer.squad.club_country ? ` (${selectedPlayer.squad.club_country})` : ""}`
                        : "–" },
                    { label: "Age", value: selectedPlayer.squad.age ?? "–" },
                    { label: "Caps", value: selectedPlayer.squad.caps ?? "–" },
                    { label: "Int. Goals", value: selectedPlayer.squad.international_goals ?? 0 },
                    { label: "Position", value: selectedPlayer.squad.position ?? "–" },
                    { label: "Date of Birth", value: selectedPlayer.squad.date_of_birth ?? "–" },
                  ].map((s) => (
                    <div key={s.label}>
                      <p className="text-muted text-xs">{s.label}</p>
                      <p className="text-text font-semibold">{String(s.value)}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-muted text-sm self-center">
                  No squad data found for this player.
                </p>
              )}
            </div>
          )}
        </div>
      )}

      {/* ── Form tab ─────────────────────────────────────── */}
      {tab === "form" && (
        <div className="bg-surface border border-border rounded-xl p-6">
          <h2 className="text-lg font-semibold mb-5">Last {form.length} Matches</h2>
          {form.length === 0 ? (
            <p className="text-muted">No form data available.</p>
          ) : (
            <>
              {/* Result strip */}
              <div className="flex gap-2 mb-6 flex-wrap">
                {[...form].reverse().map((f, i) => (
                  <div
                    key={i}
                    className={`w-9 h-9 rounded-lg flex items-center justify-center font-bold text-sm ${RESULT_COLOR[f.result]}`}
                    title={`${f.date}: ${f.result} vs ${f.opponent} (${f.goals_for}–${f.goals_against})`}
                  >
                    {f.result}
                  </div>
                ))}
              </div>

              {/* Form table */}
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-muted border-b border-border">
                      <th className="text-left py-2 pr-4">Date</th>
                      <th className="text-left py-2 pr-4">Opponent</th>
                      <th className="py-2 pr-4">Venue</th>
                      <th className="py-2 pr-4">Score</th>
                      <th className="py-2">Result</th>
                    </tr>
                  </thead>
                  <tbody>
                    {[...form].reverse().map((f, i) => (
                      <tr key={i} className="border-b border-border/40 hover:bg-surface2 transition-colors">
                        <td className="py-2.5 pr-4 text-muted">{f.date}</td>
                        <td className="py-2.5 pr-4">
                          <TeamFlag name={f.opponent} size="sm" />
                        </td>
                        <td className="py-2.5 pr-4 text-muted text-center">{f.venue}</td>
                        <td className="py-2.5 pr-4 text-center font-mono font-semibold">
                          {f.goals_for}–{f.goals_against}
                        </td>
                        <td className="py-2.5 text-center">
                          <span className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-bold ${RESULT_COLOR[f.result]}`}>
                            {f.result}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Summary */}
              {form.length > 0 && (
                <div className="flex gap-6 mt-6 text-sm">
                  {[
                    { label: "Wins",   value: form.filter((f) => f.result === "W").length, color: "text-green-400" },
                    { label: "Draws",  value: form.filter((f) => f.result === "D").length, color: "text-yellow-400" },
                    { label: "Losses", value: form.filter((f) => f.result === "L").length, color: "text-red-400" },
                    { label: "Scored",   value: form.reduce((s, f) => s + f.goals_for, 0),     color: "text-accent" },
                    { label: "Conceded", value: form.reduce((s, f) => s + f.goals_against, 0), color: "text-muted" },
                  ].map((m) => (
                    <div key={m.label} className="text-center">
                      <div className={`text-xl font-bold ${m.color}`}>{m.value}</div>
                      <div className="text-muted text-xs">{m.label}</div>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* ── Ranking tab ───────────────────────────────────── */}
      {tab === "ranking" && (
        <div className="bg-surface border border-border rounded-xl p-6">
          <h2 className="text-lg font-semibold mb-5">FIFA Ranking History</h2>
          <RankingChart data={rankings} teamName={teamName} />
        </div>
      )}

      {/* ── Squad tab ─────────────────────────────────────── */}
      {tab === "squad" && (
        <div className="bg-surface border border-border rounded-xl p-6">
          <div className="flex items-center justify-between mb-5">
            <h2 className="text-lg font-semibold">
              Squad ({squad?.players.length ?? 0} players)
            </h2>
            <div className="flex gap-1 bg-surface2 rounded-lg p-1">
              {["All", "GK", "DEF", "MID", "FWD"].map((p) => (
                <button
                  key={p}
                  onClick={() => setPosFilter(p)}
                  className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
                    posFilter === p ? "bg-accent text-white" : "text-muted hover:text-text"
                  }`}
                >
                  {p}
                </button>
              ))}
            </div>
          </div>

          {filteredSquad.length === 0 ? (
            <p className="text-muted">No players found.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-muted border-b border-border text-left">
                    <th className="py-2 pr-3 w-8">#</th>
                    <th className="py-2 pr-3">Pos</th>
                    <th className="py-2 pr-4">Name</th>
                    <th className="py-2 pr-4 text-center">Age</th>
                    <th className="py-2 pr-4 text-center">Caps</th>
                    <th className="py-2 pr-4 text-center">Goals</th>
                    <th className="py-2">Club</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredSquad.map((p, i) => (
                    <tr key={i} className="border-b border-border/40 hover:bg-surface2 transition-colors">
                      <td className="py-2.5 pr-3 text-muted text-sm">
                        {p.squad_number ?? "–"}
                      </td>
                      <td className="py-2.5 pr-3">
                        {p.position && (
                          <span className={`text-xs px-2 py-0.5 rounded-full font-bold ${POS_COLOR[p.position] ?? ""}`}>
                            {p.position}
                          </span>
                        )}
                      </td>
                      <td className="py-2.5 pr-4 font-medium text-text">{p.player_name}</td>
                      <td className="py-2.5 pr-4 text-center text-muted">{p.age ?? "–"}</td>
                      <td className="py-2.5 pr-4 text-center text-muted">{p.caps ?? "–"}</td>
                      <td className="py-2.5 pr-4 text-center text-muted">
                        {(p.international_goals ?? 0) > 0 ? (
                          <span className="text-gold font-semibold">{p.international_goals}</span>
                        ) : (
                          "–"
                        )}
                      </td>
                      <td className="py-2.5 text-muted text-sm">
                        {p.club ?? "–"}
                        {p.club_country && (
                          <span className="text-muted/60 ml-1">({p.club_country})</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* ── H2H tab ────────────────────────────────────────── */}
      {tab === "h2h" && (
        <div className="bg-surface border border-border rounded-xl p-6">
          <h2 className="text-lg font-semibold mb-5">Head-to-Head vs Group Opponents</h2>
          {h2hRecords.length === 0 ? (
            <p className="text-muted">No H2H data available.</p>
          ) : (
            <div className="space-y-4">
              {h2hRecords.map((r, i) => {
                const isTeamA = r.team_a === teamName;
                const opponent = isTeamA ? r.team_b : r.team_a;
                const wins   = isTeamA ? r.a_wins  : r.b_wins;
                const losses = isTeamA ? r.b_wins  : r.a_wins;
                const gf     = isTeamA ? r.a_goals : r.b_goals;
                const ga     = isTeamA ? r.b_goals : r.a_goals;
                const totalPct = r.n_played > 0
                  ? Math.round((wins / r.n_played) * 100) : 0;
                const drawPct = r.n_played > 0
                  ? Math.round((r.draws / r.n_played) * 100) : 0;
                const lossPct = r.n_played > 0
                  ? Math.round((losses / r.n_played) * 100) : 0;

                return (
                  <div key={i} className="bg-surface2 border border-border rounded-xl p-5">
                    <div className="flex items-center gap-4 mb-4">
                      <TeamFlag name={teamName} size="md" showLink={false} />
                      <span className="text-muted font-bold">vs</span>
                      <TeamFlag name={opponent} size="md" />
                      <div className="ml-auto text-muted text-sm">{r.n_played} meetings</div>
                    </div>

                    {r.n_played === 0 ? (
                      <p className="text-muted text-sm">Teams have never met</p>
                    ) : (
                      <>
                        {/* W/D/L bar */}
                        <div className="flex h-3 rounded-full overflow-hidden mb-3 gap-px">
                          {totalPct > 0 && (
                            <div
                              className="bg-green-500 transition-all"
                              style={{ width: `${totalPct}%` }}
                              title={`${wins}W`}
                            />
                          )}
                          {drawPct > 0 && (
                            <div
                              className="bg-yellow-400 transition-all"
                              style={{ width: `${drawPct}%` }}
                              title={`${r.draws}D`}
                            />
                          )}
                          {lossPct > 0 && (
                            <div
                              className="bg-red-500 transition-all"
                              style={{ width: `${lossPct}%` }}
                              title={`${losses}L`}
                            />
                          )}
                        </div>

                        <div className="flex gap-6 text-sm">
                          <div className="text-center">
                            <div className="text-green-400 font-bold text-lg">{wins}</div>
                            <div className="text-muted text-xs">Wins</div>
                          </div>
                          <div className="text-center">
                            <div className="text-yellow-400 font-bold text-lg">{r.draws}</div>
                            <div className="text-muted text-xs">Draws</div>
                          </div>
                          <div className="text-center">
                            <div className="text-red-400 font-bold text-lg">{losses}</div>
                            <div className="text-muted text-xs">Losses</div>
                          </div>
                          <div className="text-center ml-4">
                            <div className="text-text font-bold text-lg">{gf}–{ga}</div>
                            <div className="text-muted text-xs">Goals (F–A)</div>
                          </div>
                          {r.last_match_date && (
                            <div className="text-center ml-4">
                              <div className="text-text font-semibold">
                                {r.last_score}
                                <span className={`ml-2 text-sm ${
                                  r.last_result_for_a === (isTeamA ? "W" : "L") ? "text-green-400" :
                                  r.last_result_for_a === "D" ? "text-yellow-400" : "text-red-400"
                                }`}>
                                  ({isTeamA ? r.last_result_for_a :
                                    r.last_result_for_a === "W" ? "L" :
                                    r.last_result_for_a === "L" ? "W" : "D"})
                                </span>
                              </div>
                              <div className="text-muted text-xs">Last match · {r.last_match_date}</div>
                            </div>
                          )}
                        </div>
                      </>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
