"""
Season-long projection: per-gameweek Expected Points for every player, for
every remaining fixture. Feeds the rank projector and transfer planner.
"""
from . import config as C
from . import fixtures as FX
from . import players as P


def build_projection(bootstrap, history, team_ratings, avg_att, avg_def,
                     fixtures, next_event):
    """
    Returns:
      rates_by_id   : {player_id: rates dict}
      event_xp      : {player_id: {event: xp}} across all remaining events
      meta_by_id    : {player_id: {name, team, pos, price, ...}}
      upcoming_all  : {team_id: [fixture dicts for all remaining events]}
    """
    games_played = sum(1 for ev in bootstrap["events"] if ev.get("finished"))
    pos_priors = P.compute_pos_priors(bootstrap, history)
    upcoming_all = FX.team_upcoming(fixtures, team_ratings, avg_att, avg_def,
                                    next_event, horizon=40)
    teams = {t["id"]: t for t in bootstrap["teams"]}

    rates_by_id, event_xp, meta_by_id = {}, {}, {}
    for el in bootstrap["elements"]:
        pid = el["id"]
        rates = P.build_player_rates(el, history.get(str(el["code"])),
                                     games_played, pos_priors)
        rates_by_id[pid] = rates
        tid = el["team"]
        by_ev = {}
        for f in upcoming_all.get(tid, []):
            r = P.xp_for_fixture(rates, f)
            by_ev[f["event"]] = by_ev.get(f["event"], 0.0) + r["xp"]
        event_xp[pid] = by_ev
        meta_by_id[pid] = {
            "id": pid,
            "name": el["web_name"],
            "team": teams[tid]["short_name"],
            "team_id": tid,
            "pos": rates["pos"],
            "price": el["now_cost"] / 10.0,
            "own": float(el["selected_by_percent"]),
            "p_start": rates["p_start"],
        }
    return rates_by_id, event_xp, meta_by_id, upcoming_all


def team_gw_points(pick_ids, event_xp, meta_by_id, event, captain_id=None,
                   bench_boost=False):
    """
    Best-XI expected points for a set of 15 player ids in one GW, choosing a
    legal formation, plus captain doubling. If bench_boost, all 15 count.
    """
    players = []
    for pid in pick_ids:
        xp = event_xp.get(pid, {}).get(event, 0.0)
        players.append((pid, meta_by_id[pid]["pos"], xp))

    if bench_boost:
        chosen = players
    else:
        chosen = _best_xi(players)

    total = 0.0
    cap_xp = 0.0
    chosen_ids = {p[0] for p in chosen}
    for pid, pos, xp in chosen:
        total += xp
        if pid == captain_id:
            cap_xp = xp
    # captain: if the named captain didn't start, model would auto-use vice;
    # approximate by doubling the highest-xp starter if captain not in XI.
    if captain_id not in chosen_ids and chosen:
        cap_xp = max(p[2] for p in chosen)
    total += cap_xp
    return total


def _best_xi(players):
    """Pick the highest-xP legal XI (1 GK, 3-5 DEF, 2-5 MID, 1-3 FWD)."""
    gk = sorted([p for p in players if p[1] == "GKP"], key=lambda x: -x[2])
    de = sorted([p for p in players if p[1] == "DEF"], key=lambda x: -x[2])
    mi = sorted([p for p in players if p[1] == "MID"], key=lambda x: -x[2])
    fw = sorted([p for p in players if p[1] == "FWD"], key=lambda x: -x[2])
    best, best_xp = None, -1
    for d in range(3, 6):
        for m in range(2, 6):
            for f in range(1, 4):
                if d + m + f != 10:
                    continue
                if len(de) < d or len(mi) < m or len(fw) < f or len(gk) < 1:
                    continue
                xi = [gk[0]] + de[:d] + mi[:m] + fw[:f]
                s = sum(p[2] for p in xi)
                if s > best_xp:
                    best_xp, best = s, xi
    return best or (gk[:1] + de + mi + fw)
