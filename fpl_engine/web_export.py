"""
Serialise the model outputs to JSON for the Next.js dashboard.
Writes two files into web/public/data/:
  - dashboard.json : everything the dashboard needs except the big player table
  - players.json   : the full player database (sortable table)
"""
import json
import math

import pandas as pd

from . import config as C


def _clean(obj):
    """Recursively make a structure JSON-safe (NaN/inf -> None)."""
    if isinstance(obj, float):
        return None if (math.isnan(obj) or math.isinf(obj)) else obj
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_clean(v) for v in obj]
    return obj


def _records(df, cols=None):
    d = df[cols] if cols else df
    d = d.where(pd.notna(d), None)
    return _clean(d.to_dict(orient="records"))


def build_web_squad(df, squad_ids, captain_id, event_xp, next_event):
    if not squad_ids:
        return [], []
    end = next_event + C.HORIZON - 1
    by_id = {int(r["id"]): r for _, r in df.iterrows()}
    rows = []
    for pid in squad_ids:
        r = by_id.get(int(pid))
        if r is None:
            continue
        rows.append({
            "id": int(pid), "name": r["name"], "team": r["team"],
            "pos": r["pos"], "price": float(r["price"]), "own": float(r["own%"]),
            "nailed": int(r["nailed"]), "xP_next": float(r["xP_next"]),
            "xP_H": float(r["xP_H"]), "status": r["status"],
            "news": r["news"] or "", "is_captain": int(pid) == (captain_id or -1),
        })
    order = {"GKP": 0, "DEF": 1, "MID": 2, "FWD": 3}
    rows.sort(key=lambda x: (order[x["pos"]], -x["xP_H"]))
    return rows, []


def write_model(ctx, event_xp, meta_by_id, df, meta, cfg, next_event):
    """
    Write a single team-agnostic model.json the dashboard uses to compute
    ANY manager's rank projection & transfers client-side from their entry id.
    """
    C.WEB_DATA_DIR.mkdir(parents=True, exist_ok=True)

    events = sorted({ev for d in event_xp.values() for ev in d.keys()})
    # per-player upcoming xP, rounded to keep the file small
    exp = {str(pid): {str(ev): round(v, 2) for ev, v in d.items() if v}
           for pid, d in event_xp.items()}

    pcols = ["id", "name", "team", "pos", "price", "own%", "form", "pts",
             "nailed", "p_start%", "xG90", "xA90", "xGI90", "DEFCON90",
             "saves90", "bonus90", "pen", "fk", "ck", "xP_next", "xP_H",
             "xP_attack", "xP_cs", "xP_defcon", "xP_bonus", "value_H",
             "status", "news"]
    players = _records(df[pcols])
    # attach p_start (0-1) for client formation/optimiser logic
    pstart = {int(pid): m["p_start"] for pid, m in meta_by_id.items()}
    for p in players:
        p["p_start"] = round(pstart.get(int(p["id"]), 0.0), 3)

    fx = {"events": ctx["tracker_evlist"], "rows": {}}
    for team, evmap in ctx["fixture_matrix"].items():
        fx["rows"][team] = {str(ev): evmap.get(ev) for ev in ctx["tracker_evlist"]}

    rankings = {t: _records(r) for t, r in ctx["rankings"]}
    optimiser = None
    if ctx["optimiser"]:
        o = ctx["optimiser"]
        optimiser = {"cost": round(float(o["cost"]), 1),
                     "xi_xp": round(float(o["xi_xp"]), 1),
                     "captain": o["captain"], "players": _records(o["df"])}

    model = {
        "meta": meta, "config": cfg, "events": events,
        "players": players, "event_xp": exp,
        "teams": _records(ctx["teams_df"]), "fixtures": fx,
        "watchlist": _records(ctx["watchlist_df"]),
        "setpieces": _records(ctx["setpiece_df"]),
        "rankings": rankings, "optimiser": optimiser,
        "chips_notes": [
            "Bench Boost: play in a good double GW where all 15 have 2 fixtures.",
            "Triple Captain: a premium at home in a double GW.",
            "Free Hit: a big blank GW, or to attack a double.",
            "Wildcard: when 4+ need changing before a fixture swing.",
        ],
    }
    (C.WEB_DATA_DIR / "model.json").write_text(
        json.dumps(_clean(model), ensure_ascii=False), encoding="utf-8")
    return C.WEB_DATA_DIR


def write_json(ctx, rank_result, transfer_result, squad_web, meta):
    C.WEB_DATA_DIR.mkdir(parents=True, exist_ok=True)
    df = ctx["df"]

    # fixture tracker -> serialisable
    fx = {"events": ctx["tracker_evlist"], "rows": {}}
    for team, evmap in ctx["fixture_matrix"].items():
        fx["rows"][team] = {str(ev): evmap.get(ev) for ev in ctx["tracker_evlist"]}

    rankings = {}
    for title, rdf in ctx["rankings"]:
        rankings[title] = _records(rdf)

    optimiser = None
    if ctx["optimiser"]:
        o = ctx["optimiser"]
        optimiser = {"cost": round(float(o["cost"]), 1),
                     "xi_xp": round(float(o["xi_xp"]), 1),
                     "captain": o["captain"], "players": _records(o["df"])}

    dashboard = {
        "meta": meta,
        "rank": rank_result,
        "transfers": transfer_result,
        "squad": squad_web,
        "teams": _records(ctx["teams_df"]),
        "fixtures": fx,
        "watchlist": _records(ctx["watchlist_df"]),
        "setpieces": _records(ctx["setpiece_df"]),
        "rankings": rankings,
        "optimiser": optimiser,
        "chips_notes": [
            "Bench Boost: play in a good double GW where all 15 have 2 fixtures.",
            "Triple Captain: a premium at home in a double GW.",
            "Free Hit: a big blank GW, or to attack a double.",
            "Wildcard: when 4+ need changing before a fixture swing.",
        ],
    }

    players_cols = ["id", "name", "team", "pos", "price", "own%", "form", "pts",
                    "nailed", "p_start%", "xG90", "xA90", "xGI90", "DEFCON90",
                    "saves90", "bonus90", "pen", "fk", "ck", "xP_next", "xP_H",
                    "xP_attack", "xP_cs", "xP_defcon", "xP_bonus", "value_H",
                    "status", "news"]
    players = {"meta": meta, "players": _records(df[players_cols])}

    (C.WEB_DATA_DIR / "dashboard.json").write_text(
        json.dumps(_clean(dashboard), ensure_ascii=False), encoding="utf-8")
    (C.WEB_DATA_DIR / "players.json").write_text(
        json.dumps(_clean(players), ensure_ascii=False), encoding="utf-8")
    return C.WEB_DATA_DIR
