"""
Transfer planner.

- 'This week': every legal single swap ranked by expected points gained over
  the next HORIZON gameweeks, with a hit (-4) break-even analysis.
- '5-GW plan': a greedy forward path applying one free transfer per week.

Sell prices are approximated as current price (the FPL 'my-team' selling price
needs auth); this is slightly conservative and flagged in the output.
"""
from . import config as C


def _horizon_xp(pid, event_xp, start, end):
    d = event_xp.get(pid, {})
    return sum(d.get(e, 0.0) for e in range(start, end + 1))


def _club_counts(ids, meta):
    counts = {}
    for pid in ids:
        t = meta[pid]["team"]
        counts[t] = counts.get(t, 0) + 1
    return counts


def _best_swaps(squad_ids, bank, event_xp, meta, all_ids_by_pos, start, end,
                top=10):
    squad = set(squad_ids)
    counts = _club_counts(squad_ids, meta)
    swaps = []
    for out in squad_ids:
        mo = meta[out]
        out_xp = _horizon_xp(out, event_xp, start, end)
        budget = bank + mo["price"]
        for cand in all_ids_by_pos[mo["pos"]]:
            if cand in squad:
                continue
            mc = meta[cand]
            if mc["price"] > budget + 1e-6:
                continue
            # club limit after swap
            new_ct = counts.get(mc["team"], 0) + (0 if mc["team"] == mo["team"] else 1)
            if mc["team"] != mo["team"] and new_ct > C.MAX_PER_CLUB:
                continue
            if mc["p_start"] < 0.35:      # don't suggest a benchwarmer
                continue
            gain = _horizon_xp(cand, event_xp, start, end) - out_xp
            if gain <= 0.05:
                continue
            swaps.append({
                "out": mo["name"], "out_team": mo["team"], "out_pos": mo["pos"],
                "out_price": round(mo["price"], 1),
                "in": mc["name"], "in_team": mc["team"],
                "in_price": round(mc["price"], 1), "in_own": round(mc["own"], 1),
                "gain": round(gain, 2),
                "gain_after_hit": round(gain - 4, 2),
                "out_id": out, "in_id": cand,
            })
    swaps.sort(key=lambda s: -s["gain"])
    return swaps[:top]


def plan(bootstrap, entry_proj, event_xp, meta_by_id, next_event,
         squad_ids, bank):
    end = next_event + C.HORIZON - 1
    ids_by_pos = {"GKP": [], "DEF": [], "MID": [], "FWD": []}
    for pid, m in meta_by_id.items():
        ids_by_pos[m["pos"]].append(pid)
    for p in ids_by_pos:
        ids_by_pos[p].sort(key=lambda i: -_horizon_xp(i, event_xp, next_event, end))

    if not squad_ids:
        return {"available": False,
                "note": "No squad found for your entry id yet."}

    singles = _best_swaps(squad_ids, bank, event_xp, meta_by_id, ids_by_pos,
                          next_event, end, top=10)

    # ---- greedy 5-GW forward plan (1 free transfer / week, no hits) ----
    sq = list(squad_ids)
    bk = bank
    plan_rows = []
    for wk in range(C.HORIZON):
        gw = next_event + wk
        best = _best_swaps(sq, bk, event_xp, meta_by_id, ids_by_pos, gw, end, top=1)
        if best and best[0]["gain"] > 0.3:
            s = best[0]
            sq.remove(s["out_id"])
            sq.append(s["in_id"])
            bk = round(bk + s["out_price"] - s["in_price"], 1)
            plan_rows.append({"gw": gw, "out": s["out"], "in": s["in"],
                              "gain": s["gain"], "bank_after": bk})
        else:
            plan_rows.append({"gw": gw, "out": "-", "in": "hold (no clear gain)",
                              "gain": 0.0, "bank_after": bk})

    return {
        "available": True,
        "bank": round(bank, 1),
        "free_transfers": C.FREE_TRANSFERS_ASSUMED,
        "horizon": C.HORIZON,
        "single_transfers": singles,
        "plan_5gw": plan_rows,
        "note": "Sell prices approximated as current price; verify in the FPL app.",
    }
