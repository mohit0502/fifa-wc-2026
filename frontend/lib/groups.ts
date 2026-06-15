import type { Fixture, StandingRow } from "./types";
import { slugify } from "./slugify";

export const GROUP_COLORS: Record<string, string> = {
  A: "#ef4444",
  B: "#f97316",
  C: "#eab308",
  D: "#22c55e",
  E: "#14b8a6",
  F: "#0ea5e9",
  G: "#a855f7",
  H: "#ec4899",
  I: "#f59e0b",
  J: "#06b6d4",
  K: "#84cc16",
  L: "#94a3b8",
};

export const CONF_COLORS: Record<string, string> = {
  UEFA:     "#3b82f6",
  CONMEBOL: "#22c55e",
  CONCACAF: "#f97316",
  CAF:      "#f59e0b",
  AFC:      "#ec4899",
  OFC:      "#14b8a6",
};

export const GROUPS_ORDER = [
  "Group A", "Group B", "Group C", "Group D",
  "Group E", "Group F", "Group G", "Group H",
  "Group I", "Group J", "Group K", "Group L",
];

export const GROUP_TEAMS: Record<string, string[]> = {
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
};

export function computeStandings(
  fixtures: Fixture[],
  groupName: string,
  teams: string[]
): StandingRow[] {
  const stats: Record<string, StandingRow> = {};
  for (const t of teams) {
    stats[t] = { team: t, slug: slugify(t), P: 0, W: 0, D: 0, L: 0, GF: 0, GA: 0, GD: 0, Pts: 0 };
  }

  for (const f of fixtures) {
    if (f.group !== groupName || f.status !== "completed") continue;
    if (f.home_score === null || f.away_score === null) continue;

    const h = stats[f.home_team];
    const a = stats[f.away_team];
    if (!h || !a) continue;

    h.P++; h.GF += f.home_score; h.GA += f.away_score;
    a.P++; a.GF += f.away_score; a.GA += f.home_score;

    if (f.home_score > f.away_score) {
      h.W++; h.Pts += 3; a.L++;
    } else if (f.home_score === f.away_score) {
      h.D++; h.Pts++; a.D++; a.Pts++;
    } else {
      a.W++; a.Pts += 3; h.L++;
    }
    h.GD = h.GF - h.GA;
    a.GD = a.GF - a.GA;
  }

  return Object.values(stats).sort(
    (a, b) => b.Pts - a.Pts || b.GD - a.GD || b.GF - a.GF
  );
}
