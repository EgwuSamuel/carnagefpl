"""
The mathematical model.

Two layers:
  1. TEAM ratings  -> attack & defence strength per team (blend of FPL's 1-5
     preseason rating and season-to-date xG), used for fixture difficulty and
     clean-sheet probabilities.
  2. PLAYER model  -> blended per-90 rates (this season + last season) turned
     into an Expected Points (xP) value for a specific fixture via Poisson.
"""
import math
import statistics

from . import config as C


# ---------------------------------------------------------------------------
# Poisson helpers
# ---------------------------------------------------------------------------
def poisson_pmf(k, lam):
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return math.exp(-lam) * lam ** k / math.factorial(k)


def poisson_p_zero(lam):
    """P(exactly 0 events) -> used for clean-sheet probability."""
    return math.exp(-lam) if lam > 0 else 1.0


def poisson_p_at_least(threshold, lam):
    """P(X >= threshold) for X ~ Poisson(lam). Used for DEFCON probability."""
    if lam <= 0:
        return 0.0
    # sum the tail via complement of the head (threshold is small: 10-12)
    head = sum(poisson_pmf(k, lam) for k in range(0, int(threshold)))
    return max(0.0, 1.0 - head)


def blend(current, last, weight_current):
    """Weighted blend, gracefully handling missing sides."""
    if current is None and last is None:
        return None
    if current is None:
        return last
    if last is None:
        return current
    return weight_current * current + (1.0 - weight_current) * last


def safe_float(v, default=0.0):
    try:
        f = float(v)
        return f if math.isfinite(f) else default
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# TEAM ratings
# ---------------------------------------------------------------------------
def build_team_ratings(bootstrap, games_played):
    """
    Returns {team_id: {...ratings...}} where attack/defence are expressed as
    'expected goals vs an average opponent, neutral venue'.
    """
    teams = {t["id"]: t for t in bootstrap["teams"]}
    els = bootstrap["elements"]

    # Season-to-date team xG for (sum of players' expected_goals) and
    # xG against (median of DEF/GK expected_goals_conceded_per_90 * games).
    by_team = {}
    for e in els:
        by_team.setdefault(e["team"], []).append(e)

    weight_cur = min(games_played / C.TEAM_FULL_TRUST_GAMES,
                     C.TEAM_MAX_CURRENT_WEIGHT) if games_played > 0 else 0.0

    ratings = {}
    for tid, t in teams.items():
        squad = by_team.get(tid, [])
        # --- priors from FPL 1-5 overall strength (home/away averaged) ---
        s_home = t.get("strength_overall_home") or t.get("strength") or 3
        s_away = t.get("strength_overall_away") or t.get("strength") or 3
        s = (s_home + s_away) / 2.0
        prior_att = C.prior_attack(s)
        prior_def = C.prior_defence(s)

        # --- current-season signal ---
        cur_att = cur_def = None
        if games_played > 0 and squad:
            xgf = sum(safe_float(e["expected_goals"]) for e in squad)
            cur_att = xgf / games_played if games_played else None
            def_rates = [safe_float(e["expected_goals_conceded_per_90"])
                         for e in squad
                         if e["element_type"] in (1, 2) and e["minutes"] > 0]
            if def_rates:
                cur_def = statistics.median(def_rates)

        att = blend(cur_att, prior_att, weight_cur) or prior_att
        dfn = blend(cur_def, prior_def, weight_cur) or prior_def
        ratings[tid] = {
            "id": tid,
            "name": t["name"],
            "short": t["short_name"],
            "fpl_strength": s,
            "attack": att,       # expected goals scored vs avg opp
            "defence": dfn,      # expected goals conceded vs avg opp
        }

    # League averages for normalisation
    avg_att = statistics.mean(r["attack"] for r in ratings.values())
    avg_def = statistics.mean(r["defence"] for r in ratings.values())
    for r in ratings.values():
        r["attack_idx"] = r["attack"] / avg_att if avg_att else 1.0
        r["defence_idx"] = r["defence"] / avg_def if avg_def else 1.0
    return ratings, avg_att, avg_def


def expected_goals_conceded(team_r, opp_r, is_home, league_avg_att):
    """Expected goals a team concedes in a specific fixture (their λ_against)."""
    base = team_r["defence"]                       # their concession vs avg opp
    opp_quality = opp_r["attack"] / league_avg_att  # scale by opponent attack
    venue = C.HOME_DEFENCE_MULT if is_home else C.AWAY_DEFENCE_MULT
    return max(0.05, base * opp_quality * venue)


def attack_fixture_mult(opp_r, is_home, league_avg_def):
    """Multiplier on a player's baseline xG/xA for a given fixture."""
    opp_weakness = opp_r["defence"] / league_avg_def
    venue = C.HOME_ATTACK_MULT if is_home else C.AWAY_ATTACK_MULT
    return opp_weakness * venue
