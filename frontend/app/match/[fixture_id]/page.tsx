"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import TeamFlag from "@/components/TeamFlag";
import GroupBadge from "@/components/GroupBadge";
import { getFlagUrl } from "@/lib/flags";
import { slugify } from "@/lib/slugify";
import { GROUP_COLORS } from "@/lib/groups";
import type { Fixture, FormEntry, H2HRecord, TeamFeatures, MatchPrediction } from "@/lib/types";

type Tab = "overview" | "lineups" | "h2h";

type LineupPlayer = { pos: string; name: string; short_name: string; injury: string | null };
type Lineup = {
  status: string;
  formation: string;
  scraped_at?: string;
  players: LineupPlayer[];
  injuries: LineupPlayer[];
};

const RESULT_COLOR: Record<string, string> = {
  W: "bg-green-500/20 text-green-400",
  D: "bg-yellow-500/20 text-yellow-400",
  L: "bg-red-500/20 text-red-400",
};


export default function MatchCentrePage() {
  const { fixture_id } = useParams() as { fixture_id: string };
  const fixtureId = parseInt(fixture_id, 10);

  const [fixture, setFixture] = useState<Fixture | null>(null);
  const [homeForm, setHomeForm] = useState<FormEntry[]>([]);
  const [awayForm, setAwayForm] = useState<FormEntry[]>([]);
  const [homeFeats, setHomeFeats] = useState<TeamFeatures | null>(null);
  const [awayFeats, setAwayFeats] = useState<TeamFeatures | null>(null);
  const [h2h, setH2h] = useState<H2HRecord | null>(null);
  const [homeLineup, setHomeLineup] = useState<Lineup | null>(null);
  const [awayLineup, setAwayLineup] = useState<Lineup | null>(null);
  const [prediction, setPrediction] = useState<MatchPrediction | null>(null);
  const [tab, setTab] = useState<Tab>("overview");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetch("/data/fixtures.json").then((r) => r.json()),
      fetch("/data/form.json").then((r) => r.json()),
      fetch("/data/team_features.json").then((r) => r.json()),
      fetch("/data/h2h.json").then((r) => r.json()),
      fetch("/data/lineups.json").then((r) => r.json()),
      fetch("/data/predictions.json").then((r) => r.json()),
    ]).then(([fixtures, formMap, feats, h2hAll, lineups, preds]) => {
      const fx = (fixtures as Fixture[]).find((f) => f.fixture_id === fixtureId) ?? null;
      setFixture(fx);
      setPrediction(preds?.fixtures?.[fixtureId] ?? null);
      if (fx) {
        const hs = slugify(fx.home_team);
        const as_ = slugify(fx.away_team);
        setHomeForm((formMap[hs] ?? []).slice(-5));
        setAwayForm((formMap[as_] ?? []).slice(-5));
        setHomeFeats(feats[hs] ?? null);
        setAwayFeats(feats[as_] ?? null);
        setHomeLineup(lineups[hs] ?? null);
        setAwayLineup(lineups[as_] ?? null);
        const rec = (h2hAll as H2HRecord[]).find(
          (r) =>
            (r.team_a === fx.home_team && r.team_b === fx.away_team) ||
            (r.team_b === fx.home_team && r.team_a === fx.away_team)
        ) ?? null;
        setH2h(rec);
      }
      setLoading(false);
    });
  }, [fixtureId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-muted">
        Loading match data…
      </div>
    );
  }
  if (!fixture) {
    return (
      <div className="text-center py-20 text-muted">
        Fixture not found.{" "}
        <Link href="/" className="text-accent hover:underline">
          Return home
        </Link>
      </div>
    );
  }

  const done = fixture.status === "completed";
  const groupLetter = fixture.group.split(" ")[1];
  const groupColor = GROUP_COLORS[groupLetter] ?? "#64748b";

  const tabs: { key: Tab; label: string }[] = [
    { key: "overview", label: "📊 Overview" },
    { key: "lineups", label: "👕 Lineups" },
    { key: "h2h", label: "⚔️ H2H" },
  ];

  return (
    <div>
      {/* Back nav */}
      <div className="mb-5">
        <Link href="/" className="text-muted hover:text-text text-sm">
          ← Tournament Overview
        </Link>
      </div>

      {/* ── Match header ──────────────────────────────────────── */}
      <div
        className="bg-surface border border-border rounded-2xl overflow-hidden mb-6"
        style={{ borderTopColor: groupColor, borderTopWidth: 3 }}
      >
        {/* Meta bar */}
        <div className="px-6 py-3 flex flex-wrap items-center gap-3 border-b border-border text-sm text-muted">
          <GroupBadge group={fixture.group} />
          <span>
            {new Date(fixture.match_date + "T12:00:00").toLocaleDateString("en-GB", {
              weekday: "long",
              day: "numeric",
              month: "long",
              year: "numeric",
            })}
          </span>
          <span>·</span>
          <span>
            {fixture.venue}, {fixture.city}
          </span>
        </div>

        {/* Teams + score */}
        <div className="grid grid-cols-3 items-center gap-4 px-6 py-8">
          {/* Home */}
          <div className="flex flex-col items-center gap-3 text-center">
            <Link href={`/team/${slugify(fixture.home_team)}`}>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={getFlagUrl(fixture.home_team, 80)}
                alt={fixture.home_team}
                className="w-20 h-14 object-cover rounded-xl shadow-lg border border-border/50 hover:opacity-80 transition-opacity"
              />
            </Link>
            <Link
              href={`/team/${slugify(fixture.home_team)}`}
              className="text-text font-bold text-xl hover:text-accent transition-colors leading-tight"
            >
              {fixture.home_team}
            </Link>
            {homeFeats?.fifa_rank && (
              <span className="text-muted text-xs">FIFA #{homeFeats.fifa_rank}</span>
            )}
          </div>

          {/* Score / status */}
          <div className="flex flex-col items-center gap-3">
            {done ? (
              <div className="text-5xl font-extrabold text-gold font-mono tracking-tight">
                {fixture.home_score} – {fixture.away_score}
              </div>
            ) : (
              <div className="text-4xl font-bold text-muted tracking-wider">vs</div>
            )}
            <span
              className={`text-xs px-3 py-1.5 rounded-full font-bold uppercase tracking-widest ${
                done
                  ? "bg-green-500/20 text-green-400 border border-green-500/30"
                  : "bg-yellow-500/20 text-yellow-400 border border-yellow-500/30"
              }`}
            >
              {done ? "Full Time" : "Scheduled"}
            </span>
          </div>

          {/* Away */}
          <div className="flex flex-col items-center gap-3 text-center">
            <Link href={`/team/${slugify(fixture.away_team)}`}>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={getFlagUrl(fixture.away_team, 80)}
                alt={fixture.away_team}
                className="w-20 h-14 object-cover rounded-xl shadow-lg border border-border/50 hover:opacity-80 transition-opacity"
              />
            </Link>
            <Link
              href={`/team/${slugify(fixture.away_team)}`}
              className="text-text font-bold text-xl hover:text-accent transition-colors leading-tight"
            >
              {fixture.away_team}
            </Link>
            {awayFeats?.fifa_rank && (
              <span className="text-muted text-xs">FIFA #{awayFeats.fifa_rank}</span>
            )}
          </div>
        </div>

        {/* Probability bar — Dixon-Coles model output */}
        {!done && prediction && (
          <div className="px-6 pb-6">
            <div className="flex items-center justify-between text-xs mb-2">
              <span className="font-semibold text-accent">
                {(prediction.home_win * 100).toFixed(0)}%
              </span>
              <span className="flex items-center gap-1.5 text-muted/70">
                <span className="bg-green-500/20 text-green-400 text-[10px] px-1.5 py-0.5 rounded font-bold tracking-wide">
                  DC MODEL
                </span>
                <span className="italic">Dixon-Coles Poisson</span>
              </span>
              <span className="font-semibold text-red-400">
                {(prediction.away_win * 100).toFixed(0)}%
              </span>
            </div>
            <div className="flex h-3 rounded-full overflow-hidden gap-px">
              <div
                className="bg-accent rounded-l-full"
                style={{ width: `${prediction.home_win * 100}%` }}
                title={`${fixture.home_team}: ${(prediction.home_win * 100).toFixed(1)}%`}
              />
              <div
                className="bg-muted/30"
                style={{ width: `${prediction.draw * 100}%` }}
                title={`Draw: ${(prediction.draw * 100).toFixed(1)}%`}
              />
              <div
                className="bg-red-500/70 rounded-r-full"
                style={{ width: `${prediction.away_win * 100}%` }}
                title={`${fixture.away_team}: ${(prediction.away_win * 100).toFixed(1)}%`}
              />
            </div>
            <div className="flex justify-between text-xs mt-1.5">
              <span className="text-accent font-medium">Home Win</span>
              <span className="text-muted">
                Draw {(prediction.draw * 100).toFixed(0)}%
              </span>
              <span className="text-red-400 font-medium">Away Win</span>
            </div>
          </div>
        )}
      </div>

      {/* ── Tabs ─────────────────────────────────────────────── */}
      <div className="flex gap-1 mb-6 bg-surface p-1 rounded-xl border border-border w-fit">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors whitespace-nowrap ${
              tab === t.key ? "bg-accent text-white" : "text-muted hover:text-text"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* ── Overview tab ─────────────────────────────────────── */}
      {tab === "overview" && (
        <div className="space-y-5">
          {/* Recent form */}
          <div className="bg-surface border border-border rounded-xl p-5">
            <h2 className="text-xs font-semibold text-muted uppercase tracking-wider mb-5">
              Recent Form (last 5)
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-8">
              {(
                [
                  { team: fixture.home_team, form: homeForm },
                  { team: fixture.away_team, form: awayForm },
                ] as const
              ).map(({ team, form }) => (
                <div key={team}>
                  <div className="mb-3">
                    <TeamFlag name={team} size="sm" showLink />
                  </div>
                  <div className="flex gap-1.5 mb-3">
                    {form.length === 0 ? (
                      <span className="text-muted text-xs">No data</span>
                    ) : (
                      [...form].reverse().map((f, i) => (
                        <div
                          key={i}
                          className={`w-8 h-8 rounded-lg flex items-center justify-center font-bold text-xs ${RESULT_COLOR[f.result]}`}
                          title={`${f.date}: vs ${f.opponent} ${f.goals_for}–${f.goals_against}`}
                        >
                          {f.result}
                        </div>
                      ))
                    )}
                  </div>
                  <div className="space-y-1 text-xs text-muted">
                    {[...form]
                      .reverse()
                      .slice(0, 4)
                      .map((f, i) => (
                        <div key={i} className="flex items-center gap-2">
                          <span
                            className={`w-4 text-center font-bold ${
                              RESULT_COLOR[f.result].split(" ")[1]
                            }`}
                          >
                            {f.result}
                          </span>
                          <span className="flex-1 truncate">vs {f.opponent}</span>
                          <span className="font-mono shrink-0">
                            {f.goals_for}–{f.goals_against}
                          </span>
                        </div>
                      ))}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Score probability distribution */}
          {prediction && !done && (
            <div className="bg-surface border border-border rounded-xl p-5">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xs font-semibold text-muted uppercase tracking-wider">
                  Score Probability Distribution
                </h2>
                <span className="text-xs text-muted">
                  xG: <span className="text-accent font-mono">{prediction.lambda_home}</span>
                  {" – "}
                  <span className="text-red-400 font-mono">{prediction.lambda_away}</span>
                </span>
              </div>
              <div className="grid grid-cols-3 sm:grid-cols-5 gap-2">
                {Object.entries(prediction.score_probs)
                  .sort(([, a], [, b]) => b - a)
                  .map(([score, prob]) => {
                    const [h, a] = score.split("-").map(Number);
                    const isTop = score === prediction.most_likely_score;
                    const color = h > a ? "text-accent" : h === a ? "text-muted" : "text-red-400";
                    return (
                      <div
                        key={score}
                        className={`rounded-xl p-3 text-center ${
                          isTop
                            ? "bg-gold/15 border border-gold/40"
                            : "bg-surface2"
                        }`}
                      >
                        <div className={`text-lg font-bold font-mono ${color}`}>{score}</div>
                        <div className="text-xs font-semibold text-text mt-0.5">
                          {(prob * 100).toFixed(1)}%
                        </div>
                        {isTop && (
                          <div className="text-[10px] text-gold mt-0.5 font-bold uppercase tracking-wide">
                            most likely
                          </div>
                        )}
                      </div>
                    );
                  })}
              </div>
            </div>
          )}

          {/* Stats comparison */}
          <div className="bg-surface border border-border rounded-xl p-5">
            <h2 className="text-xs font-semibold text-muted uppercase tracking-wider mb-4">
              Team Stats
            </h2>
            {/* Column headers */}
            <div className="grid grid-cols-[1fr_auto_1fr] gap-4 mb-3">
              <div className="text-right">
                <TeamFlag name={fixture.home_team} size="sm" showLink={false} />
              </div>
              <div className="w-40" />
              <div>
                <TeamFlag name={fixture.away_team} size="sm" showLink={false} />
              </div>
            </div>
            {[
              {
                label: "FIFA Rank",
                home: homeFeats?.fifa_rank ? `#${homeFeats.fifa_rank}` : "–",
                away: awayFeats?.fifa_rank ? `#${awayFeats.fifa_rank}` : "–",
                homeVal: homeFeats?.fifa_rank ?? 999,
                awayVal: awayFeats?.fifa_rank ?? 999,
                lowerIsBetter: true,
              },
              {
                label: "FIFA Points",
                home: homeFeats?.current_fifa_points?.toFixed(0) ?? "–",
                away: awayFeats?.current_fifa_points?.toFixed(0) ?? "–",
                homeVal: homeFeats?.current_fifa_points ?? 0,
                awayVal: awayFeats?.current_fifa_points ?? 0,
                lowerIsBetter: false,
              },
              {
                label: "Recent Win Rate",
                home: homeFeats?.form_form_win_rate != null
                  ? `${(homeFeats.form_form_win_rate * 100).toFixed(0)}%`
                  : "–",
                away: awayFeats?.form_form_win_rate != null
                  ? `${(awayFeats.form_form_win_rate * 100).toFixed(0)}%`
                  : "–",
                homeVal: homeFeats?.form_form_win_rate ?? 0,
                awayVal: awayFeats?.form_form_win_rate ?? 0,
                lowerIsBetter: false,
              },
              {
                label: "Avg Goals Scored",
                home: homeFeats?.avg_goals_scored_20?.toFixed(1) ?? "–",
                away: awayFeats?.avg_goals_scored_20?.toFixed(1) ?? "–",
                homeVal: homeFeats?.avg_goals_scored_20 ?? 0,
                awayVal: awayFeats?.avg_goals_scored_20 ?? 0,
                lowerIsBetter: false,
              },
              {
                label: "Avg Goals Conceded",
                home: homeFeats?.avg_goals_conceded_20?.toFixed(1) ?? "–",
                away: awayFeats?.avg_goals_conceded_20?.toFixed(1) ?? "–",
                homeVal: homeFeats?.avg_goals_conceded_20 ?? 0,
                awayVal: awayFeats?.avg_goals_conceded_20 ?? 0,
                lowerIsBetter: true,
              },
              {
                label: "All-time Win Rate",
                home: homeFeats?.all_time_win_rate != null
                  ? `${(homeFeats.all_time_win_rate * 100).toFixed(0)}%`
                  : "–",
                away: awayFeats?.all_time_win_rate != null
                  ? `${(awayFeats.all_time_win_rate * 100).toFixed(0)}%`
                  : "–",
                homeVal: homeFeats?.all_time_win_rate ?? 0,
                awayVal: awayFeats?.all_time_win_rate ?? 0,
                lowerIsBetter: false,
              },
              {
                label: "WC Appearances",
                home: homeFeats?.wc_appearances_approx ?? "–",
                away: awayFeats?.wc_appearances_approx ?? "–",
                homeVal: homeFeats?.wc_appearances_approx ?? 0,
                awayVal: awayFeats?.wc_appearances_approx ?? 0,
                lowerIsBetter: false,
              },
            ].map((row) => {
              const homeBetter = row.lowerIsBetter
                ? row.homeVal < row.awayVal
                : row.homeVal > row.awayVal;
              const awayBetter = row.lowerIsBetter
                ? row.awayVal < row.homeVal
                : row.awayVal > row.homeVal;
              return (
                <div
                  key={row.label}
                  className="grid grid-cols-[1fr_auto_1fr] items-center gap-4 py-2.5 border-b border-border/40 last:border-0"
                >
                  <span
                    className={`text-sm font-semibold text-right ${
                      homeBetter ? "text-accent" : "text-text"
                    }`}
                  >
                    {String(row.home)}
                  </span>
                  <span className="text-muted text-xs text-center w-40 shrink-0">
                    {row.label}
                  </span>
                  <span
                    className={`text-sm font-semibold ${
                      awayBetter ? "text-accent" : "text-text"
                    }`}
                  >
                    {String(row.away)}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ── Lineups tab ───────────────────────────────────────── */}
      {tab === "lineups" && (
        <div className="bg-surface border border-border rounded-xl p-5">
          {!homeLineup && !awayLineup ? (
            <p className="text-muted">No lineup data available for either team.</p>
          ) : (
            <>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                {(
                  [
                    { team: fixture.home_team, lineup: homeLineup },
                    { team: fixture.away_team, lineup: awayLineup },
                  ] as const
                ).map(({ team, lineup }) => (
                  <div key={team}>
                    <div className="flex items-center gap-2 mb-4">
                      <TeamFlag name={team} size="sm" showLink />
                      {lineup && (
                        <span className="ml-auto text-muted text-xs font-mono">
                          {lineup.formation}
                        </span>
                      )}
                    </div>
                    {!lineup ? (
                      <p className="text-muted text-sm">No lineup data.</p>
                    ) : (
                      <div className="space-y-0.5">
                        {lineup.players.map((p, i) => (
                          <div
                            key={i}
                            className="flex items-center gap-2.5 px-2 py-1.5 rounded-lg hover:bg-surface2 transition-colors"
                          >
                            <span className="text-muted text-xs w-4 text-right shrink-0">
                              {i + 1}
                            </span>
                            <span className="text-xs font-bold px-1.5 py-0.5 rounded bg-surface2 text-muted w-10 text-center shrink-0">
                              {p.pos}
                            </span>
                            <span className="text-text text-sm flex-1">{p.name}</span>
                            {p.injury && (
                              <span
                                className={`text-xs font-bold px-1.5 py-0.5 rounded-full shrink-0 ${
                                  p.injury === "OUT"
                                    ? "bg-red-500/20 text-red-400"
                                    : "bg-yellow-500/20 text-yellow-400"
                                }`}
                              >
                                {p.injury}
                              </span>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
              <div className="mt-5 pt-4 border-t border-border flex items-center justify-between text-xs text-muted">
                <span>Source: RotoWire pre-tournament predictions</span>
                <div className="flex gap-4">
                  <Link
                    href={`/team/${slugify(fixture.home_team)}`}
                    className="text-accent hover:underline"
                  >
                    {fixture.home_team} full page →
                  </Link>
                  <Link
                    href={`/team/${slugify(fixture.away_team)}`}
                    className="text-accent hover:underline"
                  >
                    {fixture.away_team} full page →
                  </Link>
                </div>
              </div>
            </>
          )}
        </div>
      )}

      {/* ── H2H tab ───────────────────────────────────────────── */}
      {tab === "h2h" && (
        <div className="bg-surface border border-border rounded-xl p-5">
          <h2 className="text-xs font-semibold text-muted uppercase tracking-wider mb-5">
            All-time Head-to-Head
          </h2>
          {!h2h || h2h.n_played === 0 ? (
            <p className="text-muted">These teams have never met.</p>
          ) : (
            (() => {
              const isHomeA = h2h.team_a === fixture.home_team;
              const homeWins = isHomeA ? h2h.a_wins : h2h.b_wins;
              const awayWins = isHomeA ? h2h.b_wins : h2h.a_wins;
              const homeGoals = isHomeA ? h2h.a_goals : h2h.b_goals;
              const awayGoals = isHomeA ? h2h.b_goals : h2h.a_goals;
              return (
                <div>
                  {/* Bar */}
                  <div className="flex items-center justify-between text-sm font-semibold mb-2">
                    <span className="text-accent">
                      {homeWins}W · {fixture.home_team}
                    </span>
                    <span className="text-muted text-xs">{h2h.n_played} meetings</span>
                    <span className="text-red-400">
                      {fixture.away_team} · {awayWins}W
                    </span>
                  </div>
                  <div className="flex h-3 rounded-full overflow-hidden gap-px mb-6">
                    {homeWins > 0 && (
                      <div
                        className="bg-accent"
                        style={{ width: `${(homeWins / h2h.n_played) * 100}%` }}
                        title={`${homeWins} wins`}
                      />
                    )}
                    {h2h.draws > 0 && (
                      <div
                        className="bg-muted/40"
                        style={{ width: `${(h2h.draws / h2h.n_played) * 100}%` }}
                        title={`${h2h.draws} draws`}
                      />
                    )}
                    {awayWins > 0 && (
                      <div
                        className="bg-red-500/70"
                        style={{ width: `${(awayWins / h2h.n_played) * 100}%` }}
                        title={`${awayWins} wins`}
                      />
                    )}
                  </div>

                  {/* Stat grid */}
                  <div className="grid grid-cols-3 text-center gap-6 mb-6">
                    <div>
                      <div className="text-3xl font-extrabold text-accent">{homeWins}</div>
                      <div className="text-muted text-xs mt-1">{fixture.home_team} Wins</div>
                    </div>
                    <div>
                      <div className="text-3xl font-extrabold text-muted">{h2h.draws}</div>
                      <div className="text-muted text-xs mt-1">Draws</div>
                    </div>
                    <div>
                      <div className="text-3xl font-extrabold text-red-400">{awayWins}</div>
                      <div className="text-muted text-xs mt-1">{fixture.away_team} Wins</div>
                    </div>
                  </div>

                  {/* Goals */}
                  <div className="bg-surface2 rounded-xl p-4 mb-4 text-center">
                    <div className="text-2xl font-bold text-gold">
                      {homeGoals} – {awayGoals}
                    </div>
                    <div className="text-muted text-xs mt-1">
                      Goals all-time ({fixture.home_team} – {fixture.away_team})
                    </div>
                  </div>

                  {/* Last meeting */}
                  {h2h.last_match_date && (
                    <div className="bg-surface2 rounded-xl p-4">
                      <div className="text-muted text-xs mb-2">Last meeting</div>
                      <div className="flex items-center gap-4 justify-center">
                        <TeamFlag name={fixture.home_team} size="md" showLink={false} />
                        <div className="text-center">
                          <div className="text-xl font-bold text-gold font-mono">
                            {h2h.last_score}
                          </div>
                          <div className="text-muted text-xs mt-0.5">{h2h.last_match_date}</div>
                        </div>
                        <TeamFlag name={fixture.away_team} size="md" showLink={false} />
                      </div>
                    </div>
                  )}
                </div>
              );
            })()
          )}
        </div>
      )}
    </div>
  );
}
