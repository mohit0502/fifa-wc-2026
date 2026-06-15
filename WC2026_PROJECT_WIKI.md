# FIFA World Cup 2026 — Prediction & Analytics Platform
## Project Wiki & Build Specification

*Last updated: June 2026 (v2) | Stack: Python · Supabase · GCS · GitHub Actions · Cloud Run*

---

## 1. Project Overview

An end-to-end MLOps portfolio project built around the 2026 FIFA World Cup. The platform predicts match outcomes and scores, tracks live tournament progress, surfaces player analytics, and generates optimised fantasy football squads — all updating automatically after every game.

### Core goals
- Demonstrate a full MLOps loop: data ingestion → feature engineering → model training → serving → monitoring → retraining
- Models retrain after every WC game using time-decayed + match-importance weighted training data
- Live pipeline runs daily via GitHub Actions from June 11 through July 19
- Production-ready deployment on GCP Cloud Run with Supabase as the database

---

## 2. Tech Stack

| Layer | Tool | Notes |
|---|---|---|
| Language | Python 3.11 | |
| Orchestration / CI/CD | GitHub Actions | Scheduled jobs + event triggers |
| Database | Supabase (Postgres) | Free tier, 500MB |
| Model artifact storage | GCS bucket | `wc2026-models` |
| Experiment tracking | MLflow → GCS | Hosted on Cloud Run |
| API serving | FastAPI on Cloud Run | Containerised via Docker |
| Dashboard | Next.js 14 (App Router) on Vercel | TypeScript · Tailwind CSS · Recharts |
| Models | XGBoost / LightGBM + Poisson regression | |
| Optimiser | PuLP (ILP) | Fantasy squad selection |
| LLM | Gemini 2.5 Flash | Team news summarisation |

---

## 3. Dashboard Pages

### 3.1 Tournament Overview *(landing page)*
- All 12 groups with current standings (points, GD, GF, GA)
- Full fixture schedule with dates, kickoff times, venues
- Today's games highlighted with model win probability badges
- Team advancement probabilities from Monte Carlo bracket simulator
- Entry point to match centre — click any fixture to drill in

### 3.2 Match Centre *(per fixture)*
- Your model: win %, predicted scoreline distribution
- Polymarket: live crowd-sourced win probabilities (CLOB API, updates hourly)
- Opta supercomputer: pre-tournament simulation probabilities (static, scraped once)
- Expected / confirmed starting XIs for both teams (RotoWire, visual pitch layout) — same scraper as team page, runs 2x per fixture: once 24hrs before kickoff (predicted), once 1hr before kickoff (confirmed). UI shows 'PREDICTED' vs 'CONFIRMED' badge.
- Team news summary (Gemini + web search, generated 2hrs before kickoff)
- Head-to-head record
- Recent form (last 5 games each team)

### 3.3 Bracket / Knockout Tracker
- Live bracket from Round of 32 onwards
- Advancement probabilities per team per round from Monte Carlo simulator
- Updates after every knockout game

### 3.4 Team Page *(per team, 48 pages)*
- FIFA ranking trajectory chart
- Form over last 10 games
- H2H record vs upcoming opponent
- Squad list with player cards (from Transfermarkt)
- Key stats: goals scored/conceded per game, clean sheet rate
- **Pre-tournament predicted XI** — scraped from RotoWire once before June 11, displayed as a visual pitch layout with formation. Static for the duration of the pre-tournament period. Same scraper as match centre lineups, different schedule.

### 3.5 Player Analytics
- No model — pure visualisations
- Squad composition by position, age, club, league, country
- Club representation map: which clubs have the most players at the tournament
- Market value distribution by squad
- Top scorers and assists leaders (updates live during tournament)
- Age profiles — oldest/youngest squads

### 3.6 Fantasy Optimizer
- Pre-tournament squad selector: optimal 15-player squad within $100m budget
- Per-round recommendations: Round of 32, R16, QF, SF, Final
- Two optimizer modes:
  - `optimize_full_squad()` — unlimited transfers (pre-tournament, Round of 32)
  - `optimize_transfers(current_squad, n_transfers)` — constrained swaps (all other rounds)
- Transfer allocation per round: MD2=2, MD3=2, R32=unlimited, R16=4, QF=4, SF=5, Final=6
- LLM explanation layer: Gemini generates natural language justification for each recommended squad
- Expected points methodology: model win probs × fantasy scoring rules × tournament survival probability

### 3.7 Model Performance *(MLOps page)*
- Brier score and log loss per prediction, updated after each game
- Calibration curve: predicted probability vs actual frequency
- Model version history: which version made which prediction
- Comparison chart: your model vs Polymarket vs Opta on calibration
- Running accuracy across tournament stages

---

## 4. Models

### 4.1 Match Outcome Classifier
- **Type:** XGBoost / LightGBM multiclass classifier
- **Output:** P(home win), P(draw), P(away win)
- **Training data:** Historical international results 2006–present (Kaggle martj42 dataset)
- **Sample weights:** `recency_weight × importance_weight`
  - `recency_weight = exp(-λ × days_since_match)`, λ ≈ 0.003–0.005
  - `importance_weight`: WC knockout=2.0, WC group=1.5, continental final=1.3, qualifier=1.0, friendly=0.4
- **Retraining trigger:** After every WC game, GitHub Actions appends new result and retrains
- **Versioning:** Every retrained model saved to GCS with version tag, logged in MLflow

### 4.2 Score Predictor
- **Type:** Poisson regression (one model per team, predicts expected goals)
- **Output:** λ_home, λ_away (expected goals) → scoreline probability distribution
- **Why Poisson:** Goals per match follow a Poisson distribution — standard approach in football analytics
- **Same weighting scheme** as classifier

### 4.3 Monte Carlo Bracket Simulator
- **Not a model** — uses classifier output as input
- Simulates full tournament 10,000 times
- Output: P(team reaches each round), P(team wins tournament)
- Reruns after every game

### 4.4 Fantasy Points Estimator
- **Input:** Match predictor output (expected goals, clean sheet probability, win prob) + player historical stats
- **Logic:** Distributes team-level expected goals across players proportionally based on historical goal/assist share
- **Output:** Expected fantasy points per player per remaining round
- Feeds the ILP optimizer

---

## 5. Database Schema (Supabase / Postgres)

### 5.1 `matches`
```sql
match_id              SERIAL PRIMARY KEY
match_date            DATE
home_team             TEXT  -- FK → teams.team_name
away_team             TEXT  -- FK → teams.team_name
home_score            INT
away_score            INT
outcome               TEXT  -- 'H', 'D', 'A'
tournament            TEXT  -- raw tournament name from source
tournament_type       TEXT  -- 'wc_knockout', 'wc_group', 'continental', 'qualifier', 'friendly'
importance_weight     FLOAT
stage                 TEXT
city                  TEXT
country               TEXT
neutral_venue         BOOL
extra_time            BOOL
penalty_shootout      BOOL
shootout_winner       TEXT
recency_weight        FLOAT
sample_weight         FLOAT -- recency_weight × importance_weight
data_source           TEXT  -- 'kaggle_historical' | 'api_football_live'
```

### 5.2 `teams`
```sql
team_name             TEXT PRIMARY KEY
confederation         TEXT
wc_appearances        INT
wc_wins               INT
wc_finals             INT
avg_goals_scored_5yr  FLOAT
avg_goals_conceded_5yr FLOAT
form_last10           FLOAT -- win rate last 10 games
home_win_rate         FLOAT
away_win_rate         FLOAT
neutral_win_rate      FLOAT
total_matches_played  INT
current_elo           FLOAT
last_updated          TIMESTAMP
```

### 5.3 `fifa_rankings`
```sql
ranking_id            SERIAL PRIMARY KEY
team_name             TEXT  -- FK → teams.team_name
ranking_date          DATE
rank                  INT
total_points          FLOAT
previous_points       FLOAT
rank_change           INT
```
> Critical: store one row per team per ranking release date. Join to matches on ranking that was current at match_date to avoid leaking future information into training features.

### 5.4 `players`
```sql
player_id             SERIAL PRIMARY KEY
team_name             TEXT  -- FK → teams.team_name
player_name           TEXT
position              TEXT  -- 'GK', 'DEF', 'MID', 'FWD'
age                   INT
club                  TEXT
club_league           TEXT
club_country          TEXT
caps                  INT
international_goals   INT
club_market_value_eur FLOAT
is_squad_member_2026  BOOL
fantasy_price         FLOAT  -- from FIFA fantasy game
fantasy_position      TEXT   -- official fantasy position (may differ from real position)
club_starts_last10    INT    -- from FBref 2025-26 dataset
club_goals_per90      FLOAT  -- from FBref 2025-26 dataset
club_assists_per90    FLOAT  -- from FBref 2025-26 dataset
club_xg_per90         FLOAT  -- from FBref 2025-26 dataset
intl_start_rate_last5 FLOAT  -- computed from martj42 + Fjelstul data
starter_score         FLOAT  -- composite score for probable lineup ranking
data_source           TEXT
```

### 5.5 `lineups`
```sql
lineup_id             SERIAL PRIMARY KEY
match_id              INT       -- null for pre-tournament team page lineups
team_name             TEXT      -- FK → teams.team_name
lineup_type           TEXT      -- 'pre_tournament' | 'pre_match_predicted' | 'pre_match_confirmed'
formation             TEXT      -- '4-3-3', '4-2-3-1' etc
players               JSONB     -- [{name, position, shirt_number, status, injury_flag}]
scraped_at            TIMESTAMP
source                TEXT      -- 'rotowire'
```
> JSONB for players array keeps schema flexible — RotoWire structure varies slightly per fixture. `match_id` is null for pre-tournament team page lineups, populated for all match centre lineups.

### 5.6 `predictions`
```sql
prediction_id         SERIAL PRIMARY KEY
match_id              INT   -- FK → matches.match_id
predicted_at          TIMESTAMP
model_version         TEXT
prob_home_win         FLOAT
prob_draw             FLOAT
prob_away_win         FLOAT
predicted_home_goals  FLOAT
predicted_away_goals  FLOAT
polymarket_home_win   FLOAT  -- snapshot at prediction time
polymarket_draw       FLOAT
polymarket_away_win   FLOAT
actual_outcome        TEXT   -- filled after game
actual_home_goals     INT    -- filled after game
actual_away_goals     INT    -- filled after game
brier_score           FLOAT  -- filled after game
log_loss              FLOAT  -- filled after game
is_wc2026_game        BOOL
```

### 5.7 `fantasy_squads`
```sql
squad_id              SERIAL PRIMARY KEY
round                 TEXT      -- see transfer windows table below
generated_at          TIMESTAMP
player_ids            INT[]     -- array of player_ids (15 total)
total_cost            FLOAT
expected_points       FLOAT
optimizer_version     TEXT
optimizer_mode        TEXT      -- 'full_rebuild' | 'constrained_swap'
transfers_used        INT       -- null for full rebuilds, 1–6 for constrained swaps
previous_squad_id     INT       -- FK → fantasy_squads.squad_id, null for full rebuilds
llm_explanation       TEXT      -- Gemini-generated natural language justification
```

**Transfer windows and optimizer mode per round:**

| Round | `round` value | Transfers allowed | Optimizer mode | Budget |
|---|---|---|---|---|
| Pre-tournament | `pre_tournament` | Unlimited | `full_rebuild` | $100m |
| Before Matchday 2 | `matchday_2` | 2 | `constrained_swap` | $100m |
| Before Matchday 3 | `matchday_3` | 2 | `constrained_swap` | $100m |
| Before Round of 32 | `round_of_32` | Unlimited | `full_rebuild` | $105m |
| Before Round of 16 | `round_of_16` | 4 | `constrained_swap` | $105m |
| Before Quarterfinals | `quarterfinals` | 4 | `constrained_swap` | $105m |
| Before Semifinals | `semifinals` | 5 | `constrained_swap` | $105m |
| Before Final | `final` | 6 | `constrained_swap` | $105m |

> `full_rebuild` calls `optimize_full_squad()` — picks best 15 from scratch ignoring previous squad.  
> `constrained_swap` calls `optimize_transfers(current_squad, n_transfers)` — finds optimal N swaps from current squad.

---

## 6. Project Folder Structure

```
wc2026/
├── .github/
│   └── workflows/
│       ├── daily_pipeline.yml          ← runs every morning during tournament
│       ├── retrain_on_result.yml       ← triggers after each game result
│       ├── pre_tournament_setup.yml    ← one-time historical data load
│       └── deploy.yml                 ← build + push Docker image to Cloud Run
│
├── data/
│   ├── raw/                           ← downloaded source files, never modified
│   │   ├── results.csv                ← martj42 Kaggle dataset
│   │   ├── goalscorers.csv
│   │   ├── shootouts.csv
│   │   ├── fifa_rankings.csv          ← historical rankings Kaggle dataset
│   │   ├── elo_ratings.csv            ← Elo ratings Kaggle dataset
│   │   └── wc2026_squads.csv          ← scraped from Transfermarkt post June 2
│   └── processed/                     ← cleaned, feature-engineered outputs
│       ├── training_data.parquet
│       └── team_features.parquet
│
├── ingestion/
│   ├── load_historical.py             ← Phase 1: load raw CSVs → Supabase
│   ├── scrape_squads.py               ← Transfermarkt squad scraper
│   ├── scrape_lineups.py              ← RotoWire lineup scraper (game day)
│   ├── scrape_fantasy_prices.py       ← FIFA fantasy player prices
│   ├── fetch_results.py               ← API-Football live results
│   ├── fetch_polymarket.py            ← Polymarket CLOB API odds
│   └── team_name_map.py               ← normalisation: 'USA' → 'United States' etc
│
├── features/
│   ├── build_features.py              ← feature engineering pipeline
│   ├── compute_weights.py             ← recency + importance weight calculation
│   └── update_team_features.py        ← recomputes teams table after each game
│
├── models/
│   ├── train_classifier.py            ← XGBoost/LightGBM win probability model
│   ├── train_score_predictor.py       ← Poisson regression score model
│   ├── monte_carlo.py                 ← bracket simulator
│   ├── evaluate.py                    ← brier score, log loss, calibration
│   └── registry.py                    ← save/load models to/from GCS
│
├── fantasy/
│   ├── expected_points.py             ← player xP calculator
│   ├── optimizer.py                   ← PuLP ILP optimizer (full + marginal)
│   └── explain.py                     ← Gemini explanation layer
│
├── api/
│   ├── main.py                        ← FastAPI app
│   ├── routers/
│   │   ├── predictions.py
│   │   ├── teams.py
│   │   ├── players.py
│   │   ├── fantasy.py
│   │   └── tournament.py
│   └── Dockerfile
│
├── dashboard/                         ← legacy Streamlit (kept for reference)
│
├── frontend/                          ← Next.js 14 dashboard (active)
│   ├── app/
│   │   ├── page.tsx                   ← Tournament Overview (groups + fixtures)
│   │   ├── team/[slug]/page.tsx       ← Team page (form, ranking, squad, H2H)
│   │   └── players/page.tsx          ← Player Analytics
│   ├── components/                    ← Navbar, TeamFlag, GroupBadge, charts/
│   ├── lib/                           ← types, flags, slugify, groups
│   ├── public/data/                   ← exported JSON (generated by scripts/export_data.py)
│   └── package.json
│
├── tests/
│   ├── test_ingestion.py
│   ├── test_features.py
│   ├── test_models.py
│   └── test_optimizer.py
│
├── notebooks/                         ← EDA and prototyping only, not production
│   ├── 01_eda_match_results.ipynb
│   ├── 02_eda_rankings_elo.ipynb
│   ├── 03_feature_engineering.ipynb
│   ├── 04_model_baseline.ipynb
│   └── 05_poisson_validation.ipynb
│
├── .env                               ← local only, never committed
├── .gitignore
├── requirements.txt
├── README.md
└── WIKI.md                            ← this file
```

---

## 7. Data Sources

### 7.1 Historical Data — Download Once Before June 11

#### martj42 — International Football Results 1872–2026
- **URL:** https://www.kaggle.com/datasets/martj42/international-football-results-from-1872-to-2017
- **Files:** `results.csv`, `goalscorers.csv`, `shootouts.csv`
- **What it contains:** 49,000+ international match results with date, home/away team, score, tournament name, city, country, neutral venue flag
- **How to get it:** Kaggle CLI: `kaggle datasets download martj42/international-football-results-from-1872-to-2017`
- **Save to:** `data/raw/`
- **Notes:** `tournament` column maps directly to your importance weight tiers. Contains all WC, continental tournaments, qualifiers, friendlies.

#### Historical FIFA Rankings
- **URL:** https://www.kaggle.com/datasets/cashncarry/fifaworldranking
- **Files:** `fifa_ranking-2024-06-20.csv` (or latest available)
- **What it contains:** FIFA ranking snapshots per team per release date going back to 1992
- **How to get it:** `kaggle datasets download cashncarry/fifaworldranking`
- **Save to:** `data/raw/fifa_rankings.csv`
- **Notes:** Must join to matches on ranking_date ≤ match_date to avoid data leakage

#### Elo Ratings
- **URL:** https://www.kaggle.com/datasets/datasets (search "international football elo")
- **Alternative:** http://www.eloratings.net — download the full history table
- **What it contains:** Elo rating per team per date, accounts for opponent difficulty and match importance
- **Save to:** `data/raw/elo_ratings.csv`

#### Fjelstul World Cup Database
- **URL:** https://github.com/jfjelstul/worldcup
- **Files:** Multiple CSVs — matches, goals, squads, bookings, penalty shootouts, awards
- **What it contains:** All 22 WC tournaments 1930–2022, 27 interlinked tables
- **How to get it:** `git clone https://github.com/jfjelstul/worldcup` or download ZIP
- **Save to:** `data/raw/fjelstul/`
- **Notes:** Use for player analytics dashboard — goal scorers, squad compositions per tournament

---

### 7.2 Pre-Tournament Data — Collect Before June 11

#### 2026 Squad Data (Transfermarkt)
- **Source:** Transfermarkt via `transfermarkt-scraper` Python library
- **What it contains:** 26 players per team × 48 teams — name, position, age, club, league, market value, caps, international goals
- **How to get it:** `pip install transfermarkt-scraper` then scrape each team's squad page
- **Save to:** `data/raw/wc2026_squads.csv`
- **Notes:** Squads were confirmed by FIFA on June 2. Scrape after that date.

#### FIFA Fantasy Player Prices and Positions
- **Source:** https://play.fifa.com/fantasy/team
- **What it contains:** Player name, fantasy position (GK/DEF/MID/FWD), price in $m
- **How to get it:** Scrape with Selenium or Playwright (JavaScript-rendered page)
- **Save to:** `data/raw/fantasy_prices.csv`
- **Notes:** Prices are fixed for the whole tournament — scrape once. Fantasy positions may differ from real positions (e.g. Mbappé may be MID not FWD).

#### FBref 2025-2026 Player Stats (Big 5 European Leagues)
- **URL:** https://www.kaggle.com/datasets/hubertsidorowicz/football-players-stats-2025-2026
- **Files:** `players_data_light-2025_2026.csv`
- **What it contains:** Goals, assists, xG, xA, matches played, starts, minutes per 90 for 500+ players across Premier League, La Liga, Bundesliga, Serie A, Ligue 1
- **How to get it:** `kaggle datasets download hubertsidorowicz/football-players-stats-2025-2026`
- **Save to:** `data/raw/fbref_club_stats_2526.csv`
- **Notes:** Updated weekly on Kaggle. Used for `club_starts_last10`, `club_goals_per90`, `club_assists_per90`, `club_xg_per90` columns in `players` table. Cross-reference player names against `wc2026_squads.csv` using fuzzy matching (`rapidfuzz` library). Does not cover players from MLS, Saudi Pro League, Brazilian Serie A — these are typically fringe squad players.

#### RotoWire Pre-Tournament Predicted XIs
- **URL:** https://www.rotowire.com/soccer/lineups.php?league=WOC
- **Auth:** None — public page
- **What it contains:** Predicted starting XI per team before the tournament begins, with injury/suspension flags
- **How to use:** BeautifulSoup scrape once before June 11. Stored in `lineups` table with `lineup_type = 'pre_tournament'` and `match_id = null`. Displayed on team pages as static predicted XI visual.
- **Notes:** Same scraper as match centre lineups — just a different schedule and lineup_type flag.
- **Source:** https://theanalyst.com/articles/who-will-win-2026-fifa-world-cup-predictions-opta-supercomputer
- **What it contains:** Tournament win probability per team from 10,000 simulations, group advancement probabilities
- **How to get it:** Scrape the article once with BeautifulSoup, store as JSON
- **Save to:** `data/raw/opta_predictions.json`
- **Notes:** Static — does not update during tournament. Use for comparison on model performance page only.

---

### 7.3 Live Data — Continuous During Tournament (June 11 – July 19)

#### API-Football (Live Match Results)
- **URL:** https://rapidapi.com/api-sports/api/api-football
- **Endpoint:** `GET /fixtures?league=1&season=2026` (league=1 is FIFA World Cup)
- **Auth:** RapidAPI key in `.env` as `API_FOOTBALL_KEY`
- **Free tier:** 100 requests/day — sufficient for daily result polling
- **How to use:** Poll once after last game of the day for completed fixtures. ~5–10 requests per day max.
- **Fallback:** https://github.com/openfootball/worldcup — free, no API key, community-maintained, may lag by a few hours

#### Polymarket CLOB API (Match Win Probabilities)
- **URL:** https://clob.polymarket.com/markets
- **Auth:** None required for reading
- **What it contains:** Real-time crowd-sourced win probabilities for each match
- **How to use:** Filter by WC 2026 event slug, extract yes/no prices which represent probabilities
- **Polling frequency:** Every hour during tournament via GitHub Actions schedule
- **Notes:** Per-match markets go live when fixtures are confirmed. Tournament winner market is live now.

#### RotoWire Starting Lineups
- **URL:** https://www.rotowire.com/soccer/lineups.php?league=WOC
- **Auth:** None — public page
- **What it contains:** Predicted and confirmed starting XIs per fixture, injury/suspension flags (QUES, OUT)
- **How to use:** BeautifulSoup scrape. Run twice per matchday — once 24hrs before kickoff (predicted), once 1hr before kickoff (confirmed).
- **Notes:** Build and test scraper before June 11 to confirm page structure.

#### Gemini Team News Summary
- **Source:** Gemini 2.5 Flash with web search tool enabled
- **What it contains:** Injury updates, manager press conference quotes, suspension news — 3–4 bullets per team
- **How to use:** One LLM call per fixture, 2hrs before kickoff. Prompt Gemini to search and summarise latest news for both teams.
- **Frequency:** Once per fixture, output stored in Supabase
- **GCP project:** `fa25-i535-momamaha-metadata` (same as PharmaLens)

---

## 8. GitHub Actions Workflows

### 8.1 `pre_tournament_setup.yml` — Run Once
```
Trigger: manual (workflow_dispatch)
Steps:
  1. Download and validate raw CSVs
  2. Run team name normalisation
  3. Load matches → Supabase
  4. Load FIFA rankings → Supabase
  5. Load Elo ratings → Supabase
  6. Scrape and load squads → Supabase
  7. Scrape fantasy prices → Supabase
  8. Run EDA validation checks
  9. Train initial models
  10. Save models to GCS
  11. Log run to MLflow
```

### 8.2 `daily_pipeline.yml` — Every Day During Tournament
```
Trigger: cron '0 9 * * *' (9am UTC, 5am ET)
Steps:
  1. Fetch yesterday's completed results (API-Football)
  2. Append new results to Supabase matches table
  3. Update team features (form, rolling stats)
  4. Retrain classifier + score predictor with new sample weights
  5. Save new model version to GCS, log to MLflow
  6. Run Monte Carlo bracket simulation
  7. Write new predictions for today's fixtures to Supabase
  8. Compute brier score / log loss for yesterday's predictions
  9. Scrape RotoWire lineups for today's fixtures
  10. Trigger Gemini team news for today's fixtures
  11. Poll Polymarket for latest odds
```

### 8.3 `deploy.yml` — On Push to Main
```
Trigger: push to main branch
Steps:
  1. Run test suite
  2. Build FastAPI Docker image
  3. Build Next.js frontend (runs export_data.py then `npm run build`)
  4. Push FastAPI image to GCP Artifact Registry
  5. Deploy FastAPI to Cloud Run, deploy frontend to Vercel
```

---

## 9. Fantasy Scoring Rules (Official FIFA WC 2026)

| Event | GK | DEF | MID | FWD |
|---|---|---|---|---|
| Appearance 1–59 min | +1 | +1 | +1 | +1 |
| Appearance 60+ min | +2 | +2 | +2 | +2 |
| Goal scored | +6 | +6 | +5 | +4 |
| Goal from outside box | +1 | +1 | +1 | +1 |
| Assist | +3 | +3 | +3 | +3 |
| Clean sheet (60+ min) | +4 | +4 | +1 | 0 |
| Every 3 saves (GK) | +1 | — | — | — |
| Penalty save (GK) | +5 | — | — | — |
| Every 2 goals conceded (GK/DEF) | -1 | -1 | — | — |
| Yellow card | -1 | -1 | -1 | -1 |
| Red card | -3 | -3 | -3 | -3 |
| Own goal | -2 | -2 | -2 | -2 |
| Penalty miss | -2 | -2 | -2 | -2 |

**Squad structure:** 15 players total — 2 GK, 5 DEF, 5 MID, 3 FWD  
**Budget:** $100m pre-tournament, $105m from Round of 32 onwards  
**Formation:** Must include 1 GK and valid outfield formation from starting 11

---

## 10. Build Sequence

### Phase 1 — Data Collection (Days 1–3)
- [ ] Download martj42 results, goalscorers, shootouts CSVs
- [ ] Download FIFA rankings history CSV
- [ ] Download Elo ratings CSV
- [ ] Clone Fjelstul World Cup database
- [ ] Download FBref 2025-26 Big 5 player stats CSV
- [ ] Build team name normalisation map (resolves mismatches across datasets)
- [ ] Load all historical data into Supabase
- [ ] Scrape 2026 squad data from Transfermarkt
- [ ] Scrape fantasy player prices from FIFA fantasy site
- [ ] Scrape pre-tournament predicted XIs from RotoWire → `lineups` table (`lineup_type = 'pre_tournament'`)
- [ ] Scrape Opta pre-tournament predictions (store as static JSON)
- [ ] Build and test Polymarket polling function
- [ ] Build and test RotoWire match-day lineup scraper (predicted + confirmed)
- [ ] Build and test Gemini team news function
- [ ] Fuzzy-match FBref player names to Transfermarkt squad names → populate `starter_score` column

### Phase 2 — EDA & Cleaning (Day 4)
- [ ] Class balance analysis (H/D/A on neutral ground specifically)
- [ ] Goals per match distribution — validate Poisson assumption
- [ ] FIFA ranking gap analysis — are there missing dates?
- [ ] Team name consistency check across all joined datasets
- [ ] Baseline logistic regression on ranking differential only
- [ ] Define training cutoff (recommend 2006 onwards)
- [ ] Validate importance weight tiers against tournament column values

### Phase 3 — Models (Days 5–6)
- [ ] Build feature engineering pipeline (`features/build_features.py`)
- [ ] Compute recency + importance sample weights
- [ ] Train XGBoost/LightGBM win probability classifier
- [ ] Train Poisson regression score predictor
- [ ] Evaluate both models — brier score, log loss, calibration curve
- [ ] Build Monte Carlo bracket simulator
- [ ] Save models to GCS, log experiment to MLflow
- [ ] Write retraining trigger logic for post-game updates

### Phase 4 — Fantasy Optimizer (During Tournament)
- [ ] Build expected points calculator per player
- [ ] Build `optimize_full_squad()` — ILP full rebuild
- [ ] Build `optimize_transfers()` — ILP constrained swap
- [ ] Build Gemini explanation layer
- [ ] Test all 8 transfer windows

### Phase 5 — Dashboard (Day 7–8 + during tournament)
- [ ] Tournament overview page
- [ ] Match centre page (priority — must work June 11)
  - [ ] Win probability display (your model + Polymarket + Opta)
  - [ ] Predicted / confirmed XI visual pitch layout with PREDICTED/CONFIRMED badge
  - [ ] Team news summary panel
- [ ] Model performance page (priority — core MLOps story)
- [ ] Bracket tracker page
- [ ] Team page
  - [ ] Pre-tournament predicted XI visual pitch layout
  - [ ] Form chart, H2H, squad list
- [ ] Player analytics page
- [ ] Fantasy optimizer page

### Phase 6 — Live Pipeline (June 11 onwards)
- [ ] All GitHub Actions workflows tested and armed
- [ ] Supabase connections confirmed from Actions runners
- [ ] GCS model artifact writes confirmed from Actions runners
- [ ] First live prediction written before Mexico vs South Africa kickoff

---

## 11. Key Design Decisions

| Decision | Chosen | Rejected | Reason |
|---|---|---|---|
| Retrain strategy | Append new WC games with high recency weight, retrain full model | Fine-tune only on new games | Too few WC games (104 total) to train on alone |
| Sample weighting | `exp(-λ × days) × importance_multiplier` | Pure recency or pure importance | Both signals matter independently |
| Score prediction | Poisson regression | Neural net | Interpretable, standard in football analytics, works with small data |
| Database | Supabase (Postgres) | BigQuery, Cloud SQL | Free tier, no credits consumed, standard Postgres interface |
| Orchestration | GitHub Actions | Cloud Scheduler, Airflow | Portfolio visibility, free tier, CI/CD story |
| Container platform | Cloud Run | Kubernetes | Scales to zero, no cluster management, right size for this project |
| Player lineup source | RotoWire | Official FIFA API | RotoWire updates faster, free, no auth |
| Pre-tournament predicted XI | RotoWire scrape (one-time) | Build own lineup model | No model needed — scrape is accurate enough, saves build time |
| In-tournament match XI | RotoWire scrape (2x per fixture) | Same source as pre-tournament | Same scraper, different `lineup_type` flag and schedule |
| Lineup storage | JSONB array in `lineups` table | 11 separate player columns | Flexible — RotoWire structure varies by fixture |
| Club form data | FBref Kaggle dataset (Big 5 only) | Full API scrape per player | Pre-built weekly-updated CSV covers ~90% of WC players, zero scraping complexity |
| Fantasy optimizer modes | Two functions: `optimize_full_squad()` + `optimize_transfers()` | Single function with transfer flag | Cleaner separation — full rebuild and constrained swap are fundamentally different problems |
| Team news | Gemini + web search | Custom scraper per outlet | Scraping news is brittle; LLM aggregation is robust and maintainable |
| Opta predictions | Static pre-tournament scrape | Live API | No public per-match API; pre-tournament simulation is the useful signal |

---

*FIFA World Cup 2026 Prediction Platform — Build Wiki*  
*Built as an MLOps portfolio project demonstrating end-to-end model deployment, live retraining, and production pipeline orchestration*