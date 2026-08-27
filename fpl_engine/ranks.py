"""
Rank projection.

Calibrates the field's spread from YOUR real (points, overall_rank), then
projects your overall rank forward each gameweek (to GW38) with a Monte-Carlo
confidence band. Self-corrects every refresh as new results land.
"""
import math
import random

from . import config as C
from . import projection as PROJ


# ---- normal distribution helpers (no scipy dependency) --------------------
def _phi(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _inv_phi(p):
    """Acklam's inverse normal CDF approximation."""
    p = min(max(p, 1e-9), 1 - 1e-9)
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    plow, phigh = 0.02425, 1 - 0.02425
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
               ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    if p > phigh:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
               ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    q = p - 0.5
    r = q * q
    return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / \
           (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)


def _field_team_xp(event, event_xp, meta_by_id):
    """
    Expected points of the 'average manager' team for one GW = the OWNERSHIP
    TEMPLATE (the most-owned XI, captaining the most-owned attacker), on the
    model's own scale. This is the right field baseline: a near-template team
    holds its rank, and your edge comes from where you deviate from template.
    """
    by_pos = {"GKP": [], "DEF": [], "MID": [], "FWD": []}
    for pid, m in meta_by_id.items():
        by_pos[m["pos"]].append((m["own"], event_xp.get(pid, {}).get(event, 0.0), m))
    for p in by_pos:
        by_pos[p].sort(key=lambda x: -x[0])            # by ownership desc
    # template 3-4-3 of the most-owned players
    xi = by_pos["GKP"][:1] + by_pos["DEF"][:3] + by_pos["MID"][:4] + by_pos["FWD"][:3]
    total = sum(x[1] for x in xi)
    # captain = most-owned attacker in the XI
    attackers = by_pos["MID"][:4] + by_pos["FWD"][:3]
    cap = max(attackers, key=lambda x: x[0])[1] if attackers else 0.0
    return total + cap


def project(bootstrap, entry, history, event_xp, meta_by_id, next_event):
    total_players = bootstrap.get("total_players", 9_000_000)
    events = bootstrap["events"]
    finished = [e for e in events if e.get("finished")]
    games_played = len(finished)

    # field average cumulative to date
    field_cum_now = sum(e.get("average_entry_score") or 0 for e in finished)

    cur = history["current"] if history and history.get("current") else []
    total_now = cur[-1]["total_points"] if cur else entry.get("summary_overall_points", 0)
    rank_now = cur[-1]["overall_rank"] if cur else entry.get("summary_overall_rank", total_players // 2)
    team_value = (cur[-1]["value"] / 10.0) if cur else 100.0
    bank = (cur[-1]["bank"] / 10.0) if cur else 0.0

    # ---- calibrate field spread from your real rank ----
    z_now = _inv_phi(1 - rank_now / total_players) if rank_now else 1.0
    sd_cum_now = max((total_now - field_cum_now) / z_now, 8.0) if z_now > 0.05 else 30.0
    per_gw_field_sd = sd_cum_now / math.sqrt(max(games_played, 1))

    def sd_cum(elapsed):
        # cross-manager spread growth (skill persistence keeps this sub-linear)
        return sd_cum_now * (elapsed / max(games_played, 1)) ** C.SD_GROWTH_EXP

    # current squad from the latest finished GW's picks
    pick_ids, captain_id = _current_squad(entry, bootstrap, next_event)

    remaining = [e["id"] for e in events if e["id"] >= next_event]

    # ---- model-scale field baseline, rescaled to real points ----
    # scale so a median team maps to the real field average; then YOUR team's
    # edge is measured on the same footing as the field.
    base_model = {e: _field_team_xp(e, event_xp, meta_by_id) for e in remaining}
    scale = C.FIELD_AVG_PER_GW / base_model[next_event] if base_model.get(next_event) else 1.0
    scale = min(max(scale, 0.6), 1.8)          # guard against odd extremes

    your_model = {e: (PROJ.team_gw_points(pick_ids, event_xp, meta_by_id, e,
                                          captain_id) if pick_ids
                      else base_model[e]) for e in remaining}
    # your points = field template + a DAMPED version of your model edge
    field_mean = {e: base_model[e] * scale for e in remaining}
    your_mean = {e: field_mean[e] + (your_model[e] - base_model[e]) * scale * C.EDGE_DAMPING
                 for e in remaining}

    # ---- deterministic mean path ----
    proj = []
    ytot, ftot, elapsed = total_now, field_cum_now, games_played
    cum_your = {}
    for e in remaining:
        elapsed += 1
        ytot += your_mean[e]
        ftot += field_mean[e]
        cum_your[e] = ytot
        z = (ytot - ftot) / sd_cum(elapsed)
        rank = total_players * (1 - _phi(z))
        proj.append({"event": e, "your_pts": round(your_mean[e], 1),
                     "cum_your_pts": round(ytot, 1),
                     "cum_field_pts": round(ftot, 1),
                     "rank_p50": int(max(1, min(rank, total_players)))})

    # ---- Monte-Carlo band ----
    ranks_samples = {e: [] for e in remaining}
    field_cum_path = {}
    acc = field_cum_now
    for e in remaining:
        acc += field_mean[e]
        field_cum_path[e] = acc
    for _ in range(C.MC_SIMS):
        y = total_now
        el = games_played
        for e in remaining:
            el += 1
            y += random.gauss(your_mean[e], C.PER_GW_PLAYER_SD)
            z = (y - field_cum_path[e]) / sd_cum(el)
            ranks_samples[e].append(total_players * (1 - _phi(z)))
    for row in proj:
        s = sorted(ranks_samples[row["event"]])
        row["rank_p10"] = int(max(1, s[int(0.10 * len(s))]))
        row["rank_p90"] = int(min(total_players, s[int(0.90 * len(s))]))

    gw5_event = next_event + 4
    p5 = next((r for r in proj if r["event"] == gw5_event), proj[min(4, len(proj)-1)] if proj else None)
    p38 = proj[-1] if proj else None

    return {
        "entry": {
            "id": entry.get("id"), "name": entry.get("name"),
            "player": f"{entry.get('player_first_name','')} {entry.get('player_last_name','')}".strip(),
            "overall_points": total_now, "overall_rank": rank_now,
            "current_event": games_played, "team_value": round(team_value, 1),
            "bank": round(bank, 1), "total_players": total_players,
        },
        "history": [{"event": h["event"], "points": h["points"],
                     "total_points": h["total_points"],
                     "overall_rank": h["overall_rank"],
                     "value": h["value"] / 10.0, "bank": h["bank"] / 10.0}
                    for h in cur],
        "chips_used": [{"name": c["name"], "event": c["event"]}
                       for c in (history.get("chips") or [])],
        "calibration": {"field_cum_now": round(field_cum_now, 1),
                        "sd_cum_now": round(sd_cum_now, 1),
                        "per_gw_field_sd": round(per_gw_field_sd, 1),
                        "z_now": round(z_now, 3)},
        "projection": proj,
        "summary": {
            "rank_now": rank_now,
            "rank_gw5_p50": p5["rank_p50"] if p5 else None,
            "rank_gw5_p10": p5.get("rank_p10") if p5 else None,
            "rank_gw5_p90": p5.get("rank_p90") if p5 else None,
            "rank_gw38_p50": p38["rank_p50"] if p38 else None,
            "rank_gw38_p10": p38.get("rank_p10") if p38 else None,
            "rank_gw38_p90": p38.get("rank_p90") if p38 else None,
            "proj_final_points": p38["cum_your_pts"] if p38 else total_now,
        },
    }


def _current_squad(entry, bootstrap, next_event):
    """Return (pick_ids[15], captain_id) from the latest available picks."""
    from . import data as D
    eid = entry.get("id")
    for ev in range(next_event, 0, -1):
        picks = D.fetch_picks(eid, ev)
        if picks and picks.get("picks"):
            ids = [p["element"] for p in picks["picks"]]
            cap = next((p["element"] for p in picks["picks"] if p.get("is_captain")), None)
            return ids, cap
    return [], None
