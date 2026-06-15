export interface Fixture {
  fixture_id: number;
  group: string;
  stage: string;
  match_date: string;
  kickoff_utc: string;
  home_team: string;
  away_team: string;
  home_score: number | null;
  away_score: number | null;
  venue: string;
  city: string;
  status: "scheduled" | "completed";
}

export interface Player {
  squad_number: number | null;
  position: "GK" | "DEF" | "MID" | "FWD" | null;
  player_name: string;
  date_of_birth: string | null;
  age: number | null;
  caps: number | null;
  international_goals: number | null;
  club: string | null;
  club_country: string | null;
}

export interface Squad {
  team_name: string;
  slug: string;
  group: string;
  conf: string;
  players: Player[];
}

export interface FormEntry {
  date: string;
  opponent: string;
  venue: string;
  goals_for: number;
  goals_against: number;
  result: "W" | "D" | "L";
  tournament: string;
}

export interface RankingEntry {
  rank_date: string;
  rank: number;
  total_points: number;
}

export interface H2HRecord {
  team_a: string;
  team_b: string;
  slug_a: string;
  slug_b: string;
  n_played: number;
  a_wins: number;
  draws: number;
  b_wins: number;
  a_goals: number;
  b_goals: number;
  last_match_date: string | null;
  last_result_for_a: "W" | "D" | "L" | null;
  last_score: string | null;
}

export interface TeamMeta {
  name: string;
  slug: string;
  conf: string;
  group: string;
}

export interface GroupTeam {
  name: string;
  slug: string;
  conf: string;
}

export interface GroupInfo {
  label: string;
  teams: GroupTeam[];
}

export interface TeamFeatures {
  team_name: string;
  slug: string;
  group: string;
  conf: string;
  fifa_rank: number | null;
  current_fifa_points: number | null;
  total_matches_played: number | null;
  all_time_win_rate: number | null;
  all_time_draw_rate: number | null;
  all_time_loss_rate: number | null;
  avg_goals_scored_20: number | null;
  avg_goals_conceded_20: number | null;
  wc_appearances_approx: number | null;
  form_form_win_rate: number | null;
  form_form_goals_scored: number | null;
  form_form_goals_conceded: number | null;
}

export interface StandingRow {
  team: string;
  slug: string;
  P: number;
  W: number;
  D: number;
  L: number;
  GF: number;
  GA: number;
  GD: number;
  Pts: number;
}

export interface MatchPrediction {
  fixture_id: number;
  home_team: string;
  away_team: string;
  match_date: string;
  home_win: number;
  draw: number;
  away_win: number;
  lambda_home: number;
  lambda_away: number;
  most_likely_score: string;
  score_probs: Record<string, number>;
}

export interface PredictionsFile {
  generated_at: string;
  model: string;
  n_teams: number;
  fixtures: Record<number, MatchPrediction>;
}

export interface WcScorer {
  player_name: string;
  team_name: string;
  wc_goals: number;
}

export interface PlayerSummary {
  total_players: number;
  total_teams: number;
  total_clubs: number;
  avg_age: number;
  avg_caps: number;
  pos_counts: Record<string, number>;
  top_clubs: Array<{ club: string; count: number }>;
  top_club_countries: Array<{ club_country: string; count: number }>;
  squad_age: Array<{ team_name: string; avg_age: number; min_age: number; max_age: number }>;
  top_caps: Array<{ player_name: string; team_name: string; position: string; age: number; caps: number; international_goals: number }>;
  top_scorers: Array<{ player_name: string; team_name: string; position: string; caps: number; international_goals: number }>;
  conf_pos: Array<{ conf: string; position: string; count: number }>;
}
