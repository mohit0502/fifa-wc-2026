"""
Dixon-Coles Poisson model for football score prediction.

Reference: Dixon & Coles (1997) "Modelling Association Football Scores and
           Inefficiencies in the Football Betting Market"

Model:
    lambda_home = exp(alpha_home + beta_away + gamma * home_flag)
    lambda_away = exp(alpha_away + beta_home)

    alpha_i — attack strength of team i
    beta_i  — defensive weakness of team i (higher = easier to score against)
    gamma   — home advantage (log scale)
    rho     — Dixon-Coles low-score correlation

P(X=x, Y=y) = tau(x,y) * Poisson(x; lambda_home) * Poisson(y; lambda_away)

where tau corrects for the over-/under-representation of 0-0, 1-0, 0-1, 1-1.
"""

import pickle
from pathlib import Path

import numpy as np
from scipy.optimize import minimize
from scipy.special import gammaln
from scipy.stats import poisson


class DixonColesModel:

    def __init__(self) -> None:
        self.teams: list[str] = []
        self.alpha: dict[str, float] = {}   # attack strength
        self.beta:  dict[str, float] = {}   # defensive weakness
        self.gamma: float = 0.3             # home advantage
        self.rho:   float = -0.1            # DC correction

    # ── fit ──────────────────────────────────────────────────────────────────

    def fit(
        self,
        matches: "pd.DataFrame",
        team_list: list[str],
        reg: float = 0.01,
    ) -> "DixonColesModel":
        """
        Fit via maximum weighted log-likelihood (L-BFGS-B).

        Required columns in `matches`:
            home_team, away_team, home_score, away_score,
            neutral_venue, sample_weight
        """
        self.teams = sorted(team_list)
        n = len(self.teams)
        t2i = {t: i for i, t in enumerate(self.teams)}

        valid = matches[
            matches["home_team"].isin(t2i)
            & matches["away_team"].isin(t2i)
            & matches["home_score"].notna()
            & matches["away_score"].notna()
        ].copy()

        print(f"  Fitting on {len(valid):,} matches, {n} teams...")

        hi      = valid["home_team"].map(t2i).values
        ai      = valid["away_team"].map(t2i).values
        hg      = valid["home_score"].values.astype(int)
        ag      = valid["away_score"].values.astype(int)
        wt      = valid["sample_weight"].values
        neutral = valid["neutral_venue"].values.astype(float)

        # masks for DC low-score correction
        m00 = (hg == 0) & (ag == 0)
        m10 = (hg == 1) & (ag == 0)
        m01 = (hg == 0) & (ag == 1)
        m11 = (hg == 1) & (ag == 1)

        def neg_ll(params: np.ndarray) -> float:
            alpha = params[:n]
            beta  = params[n: 2 * n]
            gamma = params[2 * n]
            rho   = params[2 * n + 1]

            lam_h = np.exp(alpha[hi] + beta[ai] + gamma * (1 - neutral))
            lam_a = np.exp(alpha[ai] + beta[hi])

            tau = np.ones(len(valid))
            tau[m00] = np.maximum(1e-10, 1 - lam_h[m00] * lam_a[m00] * rho)
            tau[m10] = 1 + lam_a[m10] * rho
            tau[m01] = 1 + lam_h[m01] * rho
            tau[m11] = 1 - rho
            tau = np.maximum(tau, 1e-10)

            ll = wt * (
                np.log(tau)
                + hg * np.log(np.maximum(lam_h, 1e-10)) - lam_h - gammaln(hg + 1)
                + ag * np.log(np.maximum(lam_a, 1e-10)) - lam_a - gammaln(ag + 1)
            )
            # L2 regularisation to prevent parameter explosion
            penalty = reg * (np.sum(alpha ** 2) + np.sum(beta ** 2))
            return -ll.sum() + penalty

        x0 = np.zeros(2 * n + 2)
        x0[2 * n]     = 0.3    # gamma
        x0[2 * n + 1] = -0.05  # rho

        bounds = (
            [(-3.0, 3.0)] * n       # alpha
            + [(-3.0, 3.0)] * n     # beta
            + [(0.0, 1.5)]          # gamma >= 0  (home teams have advantage)
            + [(-0.95, 0.2)]        # rho
        )

        result = minimize(
            neg_ll, x0,
            method="L-BFGS-B",
            bounds=bounds,
            options={"maxiter": 10000, "maxfun": 50000, "ftol": 1e-9, "gtol": 1e-6},
        )
        print(f"  Converged: {result.success}  message: {result.message}")

        p = result.x
        for i, t in enumerate(self.teams):
            self.alpha[t] = float(p[i])
            self.beta[t]  = float(p[n + i])
        self.gamma = float(p[2 * n])
        self.rho   = float(p[2 * n + 1])
        return self

    # ── predict ──────────────────────────────────────────────────────────────

    def predict(
        self,
        home_team: str,
        away_team: str,
        neutral: bool = True,
        max_goals: int = 8,
    ) -> dict:
        """
        Return win/draw/loss probs plus full score distribution.

        Returns
        -------
        dict with:
            home_win, draw, away_win        — float, sum ≈ 1
            lambda_home, lambda_away        — Poisson means (xG proxy)
            score_probs                     — {"1-0": 0.12, ...}  top 15 scorelines
            most_likely_score               — "1-0"
        """
        a_h = self.alpha.get(home_team, 0.0)
        b_h = self.beta.get(home_team, 0.0)
        a_a = self.alpha.get(away_team, 0.0)
        b_a = self.beta.get(away_team, 0.0)
        g   = 0.0 if neutral else self.gamma

        lam_h = float(np.exp(a_h + b_a + g))
        lam_a = float(np.exp(a_a + b_h))

        # Score probability matrix P[x, y] = P(home scores x, away scores y)
        P = np.zeros((max_goals + 1, max_goals + 1))
        for x in range(max_goals + 1):
            for y in range(max_goals + 1):
                p = poisson.pmf(x, lam_h) * poisson.pmf(y, lam_a)
                # Dixon-Coles low-score correction
                if   x == 0 and y == 0: tau = 1 - lam_h * lam_a * self.rho
                elif x == 1 and y == 0: tau = 1 + lam_a * self.rho
                elif x == 0 and y == 1: tau = 1 + lam_h * self.rho
                elif x == 1 and y == 1: tau = 1 - self.rho
                else:                   tau = 1.0
                P[x, y] = max(0.0, p * tau)

        # Renormalise (tau can slightly alter total probability mass)
        P /= P.sum()

        home_win = float(np.tril(P, -1).sum())
        draw     = float(np.trace(P))
        away_win = float(np.triu(P, 1).sum())

        # Top scorelines (≥ 0.5% probability)
        score_probs = {}
        for x in range(max_goals + 1):
            for y in range(max_goals + 1):
                if P[x, y] >= 0.005:
                    score_probs[f"{x}-{y}"] = round(float(P[x, y]), 4)

        # Sort by probability descending, keep top 15
        score_probs = dict(
            sorted(score_probs.items(), key=lambda kv: kv[1], reverse=True)[:15]
        )
        most_likely = max(score_probs, key=score_probs.__getitem__) if score_probs else "1-1"

        return {
            "home_win":          round(home_win, 4),
            "draw":              round(draw, 4),
            "away_win":          round(away_win, 4),
            "lambda_home":       round(lam_h, 3),
            "lambda_away":       round(lam_a, 3),
            "score_probs":       score_probs,
            "most_likely_score": most_likely,
        }

    # ── team params table (for inspection / frontend) ─────────────────────────

    def team_params(self) -> "pd.DataFrame":
        import pandas as pd
        return pd.DataFrame(
            {
                "team":    self.teams,
                "attack":  [self.alpha[t] for t in self.teams],
                "defense": [self.beta[t]  for t in self.teams],
            }
        ).sort_values("attack", ascending=False).reset_index(drop=True)

    # ── serialisation ─────────────────────────────────────────────────────────

    def save(self, path: "Path | str") -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(self, f)
        print(f"  Saved → {path}  ({path.stat().st_size // 1024} KB)")

    @classmethod
    def load(cls, path: "Path | str") -> "DixonColesModel":
        with open(path, "rb") as f:
            obj = pickle.load(f)
        print(f"  Loaded model with {len(obj.teams)} teams")
        return obj
