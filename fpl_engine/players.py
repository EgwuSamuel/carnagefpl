"""
Player model: turn raw FPL data into blended per-90 rates and an Expected
Points (xP) value per fixture, broken down by the six routes to points.
"""
import pandas as pd

from . import config as C
from . import model as M


def _per90(total, minutes):
    if minutes and minutes > 0:
        return M.safe_float(total) / (minutes / 90.0)
    return None


# Sane per-90 caps so a lucky 1-game sample can't blow up the model.
RATE_CAPS = {"xg90": 1.0, "xa90": 0.7, "saves90": 8.0,
             "defcon90": 16.0, "bonus90": 1.5, "yellow90": 0.6}

# Hard-coded fallback priors (per-90) if the league can't supply enough data.
DEFAULT_PRIORS = {
    "xg90":   {"GKP": 0.0, "DEF": 0.03, "MID": 0.12, "FWD": 0.35},
    "xa90":   {"GKP": 0.0, "DEF": 0.05, "MID": 0.11, "FWD": 0.10},
    "saves90":{"GKP": 3.0, "DEF": 0.0,  "MID": 0.0,  "FWD": 0.0},
    "defcon90":{"GKP": 0.0,"DEF": 8.0,  "MID": 4.5,  "FWD": 2.0},
    "bonus90":{"GKP": 0.15,"DEF": 0.18, "MID": 0.22, "FWD": 0.28},
    "yellow90":{"GKP":0.05,"DEF": 0.15, "MID": 0.15, "FWD": 0.12},
}


def compute_pos_priors(bootstrap, history):
    """
    League-average per-90 rate per stat per position, from LAST season (stable),
    used as the regression target for players who lack their own history.
    """
    import statistics
    buckets = {s: {p: [] for p in ("GKP", "DEF", "MID", "FWD")}
               for s in RATE_CAPS}
    for el in bootstrap["elements"]:
        pos = C.POS[el["element_type"]]
        h = history.get(str(el["code"]))
        if not h:
            continue
        lm = M.safe_float(h.get("minutes"))
        if lm < 900:                       # only established last-season players
            continue
        vals = {
            "xg90": _per90(h.get("expected_goals"), lm),
            "xa90": _per90(h.get("expected_assists"), lm),
            "saves90": _per90(h.get("saves"), lm),
            "defcon90": _per90(h.get("defensive_contribution"), lm),
            "bonus90": _per90(h.get("bonus"), lm),
            "yellow90": _per90(h.get("yellow_cards"), lm),
        }
        for s, v in vals.items():
            if v is not None:
                buckets[s][pos].append(min(v, RATE_CAPS[s]))
    priors = {}
    for s in RATE_CAPS:
        priors[s] = {}
        for p in ("GKP", "DEF", "MID", "FWD"):
            data = buckets[s][p]
            priors[s][p] = (statistics.median(data) if len(data) >= 5
                            else DEFAULT_PRIORS[s][p])
    return priors


def build_player_rates(el, hist_row, games_played, pos_priors=DEFAULT_PRIORS):
    """Blend this-season and last-season per-90 rates for one player.

    Each rate = weight_current * current + (1 - weight_current) * prior, where
    the prior is the player's own last-season rate if available, else the
    league positional baseline. Current small-sample rates are capped so a
    single lucky match can't dominate.
    """
    pos = C.POS[el["element_type"]]
    cur_min = M.safe_float(el["minutes"])

    # ---- current-season per-90 rates (API already provides many) ----
    cur = {
        "xg90": M.safe_float(el.get("expected_goals_per_90")) if cur_min else None,
        "xa90": M.safe_float(el.get("expected_assists_per_90")) if cur_min else None,
        "saves90": M.safe_float(el.get("saves_per_90")) if cur_min else None,
        "defcon90": M.safe_float(el.get("defensive_contribution_per_90")) if cur_min else None,
        "bonus90": _per90(el.get("bonus"), cur_min),
        "yellow90": _per90(el.get("yellow_cards"), cur_min),
    }
    cur_mpg = cur_min / games_played if games_played > 0 else None

    # ---- last-season per-90 rates from history_past ----
    last = {"xg90": None, "xa90": None, "saves90": None,
            "defcon90": None, "bonus90": None, "yellow90": None}
    last_mpg = None
    if hist_row:
        lm = M.safe_float(hist_row.get("minutes"))
        if lm > 0:
            last["xg90"] = _per90(hist_row.get("expected_goals"), lm)
            last["xa90"] = _per90(hist_row.get("expected_assists"), lm)
            last["saves90"] = _per90(hist_row.get("saves"), lm)
            last["defcon90"] = _per90(hist_row.get("defensive_contribution"), lm)
            last["bonus90"] = _per90(hist_row.get("bonus"), lm)
            last["yellow90"] = _per90(hist_row.get("yellow_cards"), lm)
            last_mpg = lm / 38.0

    w = min(cur_min / C.RATE_FULL_TRUST_MINUTES,
            C.RATE_MAX_CURRENT_WEIGHT) if cur_min > 0 else 0.0

    rates = {}
    for k in cur:
        cur_v = cur[k]
        if cur_v is not None:                      # cap noisy small samples
            cur_v = min(cur_v, RATE_CAPS[k])
        last_v = last[k]
        if last_v is not None:
            last_v = min(last_v, RATE_CAPS[k])
        prior = last_v if last_v is not None else pos_priors[k][pos]
        rates[k] = M.blend(cur_v, prior, w) or 0.0
    rates["pos"] = pos

    # ---- availability & nailed-ness ----
    status = el.get("status", "a")
    chance = el.get("chance_of_playing_next_round")
    if chance is not None:
        p_avail = M.safe_float(chance) / 100.0
    elif status == "a":
        p_avail = 1.0
    elif status == "d":
        p_avail = 0.5
    else:                      # i, s, u, n
        p_avail = 0.0
    rates["p_avail"] = p_avail

    mpg = M.blend(cur_mpg, last_mpg, w)
    if mpg is None:
        mpg = 0.0
    start_rate = max(0.0, min((mpg - 10.0) / 70.0, 1.0))   # 80mpg->1.0, 45->0.5
    rates["start_rate"] = start_rate
    rates["nailed"] = round(start_rate * 100)
    rates["p_start"] = p_avail * start_rate
    rates["p_cameo"] = p_avail * (1 - start_rate) * 0.7
    rates["exp_minutes"] = (rates["p_start"] * C.STARTER_MINUTES +
                            rates["p_cameo"] * C.CAMEO_MINUTES)
    rates["weight_current"] = w
    return rates


def xp_for_fixture(rates, fx):
    """Expected points for one player in one fixture, with route breakdown."""
    pos = rates["pos"]
    p_start = rates["p_start"]
    p_cameo = rates["p_cameo"]
    exp_min = rates["exp_minutes"]
    mf = exp_min / 90.0

    # Route 6: appearance
    xp_mins = p_start * 2 + p_cameo * 1

    # Route 1: attacking returns
    goals = rates["xg90"] * mf * fx["xgf_mult"]
    assists = rates["xa90"] * mf * fx["xgf_mult"]
    xp_attack = goals * C.GOAL_PTS[pos] + assists * C.ASSIST_PTS

    # Route 2: clean sheet (needs ~60 mins => tie to p_start) + concede penalty
    lam = fx["xgc"]
    p_cs = p_start * M.poisson_p_zero(lam)
    xp_cs = p_cs * C.CS_PTS[pos]
    xp_concede = 0.0
    if pos in ("GKP", "DEF"):
        # -1 for every 2 goals conceded
        exp_hits = sum((k // 2) * M.poisson_pmf(k, lam) for k in range(0, 9))
        xp_concede = -exp_hits * p_start

    # Route 3: saves (GK) — scale by how much the opponent attacks
    xp_saves = 0.0
    if pos == "GKP":
        shots_factor = lam / C.LEAGUE_AVG_GOALS
        saves = rates["saves90"] * mf * max(0.4, shots_factor)
        xp_saves = saves / 3.0

    # Route 5: DEFCON (evaluate on the starting scenario)
    xp_defcon = 0.0
    thr = C.DEFCON_THRESHOLD[pos]
    if thr < 90 and rates["defcon90"] > 0:
        actions_if_start = rates["defcon90"] * C.STARTER_MINUTES / 90.0
        p_hit = M.poisson_p_at_least(thr, actions_if_start)
        xp_defcon = p_start * p_hit * C.DEFCON_PTS

    # Route 4: bonus (historical BPS-driven rate)
    xp_bonus = rates["bonus90"] * mf

    # Discipline
    xp_cards = -rates["yellow90"] * mf

    total = (xp_mins + xp_attack + xp_cs + xp_concede +
             xp_saves + xp_defcon + xp_bonus + xp_cards)
    return {
        "xp": total,
        "xp_mins": xp_mins,
        "xp_attack": xp_attack,
        "xp_cs": xp_cs + xp_concede,
        "xp_saves": xp_saves,
        "xp_defcon": xp_defcon,
        "xp_bonus": xp_bonus,
    }


def build_players_frame(bootstrap, history, team_ratings, upcoming,
                        next_event, games_played):
    """Assemble the master player DataFrame with model outputs."""
    teams = {t["id"]: t for t in bootstrap["teams"]}
    pos_priors = compute_pos_priors(bootstrap, history)
    rows = []
    for el in bootstrap["elements"]:
        code = str(el["code"])
        hist_row = history.get(code)
        rates = build_player_rates(el, hist_row, games_played, pos_priors)
        tid = el["team"]

        # aggregate xP over the immediate next GW and the horizon
        fx_list = upcoming.get(tid, [])
        next_fx = [f for f in fx_list if f["event"] == next_event]
        horizon_fx = [f for f in fx_list
                      if next_event <= f["event"] < next_event + C.HORIZON]

        def agg(fxs):
            tot = {"xp": 0, "xp_mins": 0, "xp_attack": 0, "xp_cs": 0,
                   "xp_saves": 0, "xp_defcon": 0, "xp_bonus": 0}
            for f in fxs:
                r = xp_for_fixture(rates, f)
                for k in tot:
                    tot[k] += r[k]
            return tot

        nxt = agg(next_fx)
        hor = agg(horizon_fx)
        price = el["now_cost"] / 10.0

        rows.append({
            "id": el["id"],
            "code": el["code"],
            "name": el["web_name"],
            "team": teams[tid]["short_name"],
            "pos": rates["pos"],
            "price": price,
            "own%": M.safe_float(el["selected_by_percent"]),
            "form": M.safe_float(el["form"]),
            "pts": el["total_points"],
            "ppg": M.safe_float(el["points_per_game"]),
            "status": el.get("status", "a"),
            "news": el.get("news", "") or "",
            "min": el["minutes"],
            "starts": el["starts"],
            "nailed": rates["nailed"],
            "p_start%": round(rates["p_start"] * 100),
            # blended per-90 rates
            "xG90": round(rates["xg90"], 3),
            "xA90": round(rates["xa90"], 3),
            "xGI90": round(rates["xg90"] + rates["xa90"], 3),
            "DEFCON90": round(rates["defcon90"], 2),
            "saves90": round(rates["saves90"], 2),
            "bonus90": round(rates["bonus90"], 2),
            # set-piece / penalty duty
            "pen": el.get("penalties_order"),
            "fk": el.get("direct_freekicks_order"),
            "ck": el.get("corners_and_indirect_freekicks_order"),
            # xP outputs
            "xP_next": round(nxt["xp"], 2),
            "xP_H": round(hor["xp"], 2),          # horizon total
            "xP_attack": round(hor["xp_attack"], 2),
            "xP_cs": round(hor["xp_cs"], 2),
            "xP_defcon": round(hor["xp_defcon"], 2),
            "xP_bonus": round(hor["xp_bonus"], 2),
            "xP_mins": round(hor["xp_mins"], 2),
            "n_fix_H": len(horizon_fx),
            "value_next": round(nxt["xp"] / price, 3) if price else 0,
            "value_H": round(hor["xp"] / price, 3) if price else 0,
        })
    df = pd.DataFrame(rows)
    return df
