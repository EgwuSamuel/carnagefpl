"""
FPL ENGINE — one-command weekly refresh.

    python fpl_refresh.py

Pulls the official FPL API, blends this-season + last-season xG / DEFCON,
runs the Expected-Points model + optimiser, and (re)writes FPL_Master.xlsx.

Edit fpl_engine/config.py to tune the model or update MY_SQUAD.
"""
import datetime as dt
import sys

import pandas as pd

from fpl_engine import config as C
from fpl_engine import data as D
from fpl_engine import model as M
from fpl_engine import fixtures as FX
from fpl_engine import players as P
from fpl_engine import optimizer as OPT
from fpl_engine import writer as W
from fpl_engine import projection as PROJ
from fpl_engine import ranks as RANKS
from fpl_engine import transfers as TR
from fpl_engine import web_export as WEB


def route_tag(row):
    parts = {"Attack": row["xP_attack"], "Clean sheet": row["xP_cs"],
             "DEFCON": row["xP_defcon"], "Bonus": row["xP_bonus"]}
    return max(parts, key=parts.get)


def build_teams_df(team_ratings, upcoming, next_event):
    rows = []
    for tid, r in team_ratings.items():
        fx = [f for f in upcoming.get(tid, [])
              if next_event <= f["event"] < next_event + 6]
        fdrs = [FX.combined_fdr(f) for f in fx]
        next6 = round(sum(fdrs) / len(fdrs), 2) if fdrs else None
        rows.append({
            "Team": r["name"],
            "Short": r["short"],
            "FPL_Strength(1-5)": round(r["fpl_strength"], 1),
            "AttackRating": round(r["attack"], 2),
            "DefenceRating(xGC)": round(r["defence"], 2),
            "Next6_FDR": next6,
            "Next6": " ".join(f["label"] for f in fx),
        })
    df = pd.DataFrame(rows).sort_values("Next6_FDR")
    return df


def build_fixture_matrix(team_ratings, upcoming, next_event, n_events=8):
    evlist = list(range(next_event, next_event + n_events))
    matrix = {}
    for tid, r in team_ratings.items():
        short = r["short"]
        matrix[short] = {}
        by_ev = {}
        for f in upcoming.get(tid, []):
            if f["event"] in evlist:
                by_ev.setdefault(f["event"], []).append(f)
        for ev, fxs in by_ev.items():
            if len(fxs) == 1:
                f = fxs[0]
                matrix[short][ev] = {"text": f["label"],
                                     "fdr": int(round(FX.combined_fdr(f)))}
            else:  # double gameweek
                text = "/".join(f["label"] for f in fxs)
                fdr = int(round(sum(FX.combined_fdr(f) for f in fxs) / len(fxs)))
                matrix[short][ev] = {"text": "DBL " + text, "fdr": fdr}
    return matrix, evlist


def build_watchlist(df):
    keep = df.copy()
    keep["route"] = keep.apply(route_tag, axis=1)
    out = []
    for team, g in keep.groupby("team"):
        g2 = g.sort_values("xP_H", ascending=False).head(3)
        out.append(g2)
    w = pd.concat(out)
    w = w.sort_values(["team", "xP_H"], ascending=[True, False])
    return w[["team", "name", "pos", "price", "own%", "route",
              "xP_next", "xP_H", "nailed"]]


def build_rankings(df):
    out = []
    avail = df[df["p_start%"] >= 40]
    for pos in ["GKP", "DEF", "MID", "FWD"]:
        d = (avail[avail["pos"] == pos]
             .sort_values("xP_H", ascending=False)
             .head(12)[["name", "team", "price", "own%", "xP_next", "xP_H"]])
        out.append((f"Best {pos} (xP over horizon)", d))
    val = (df[(df["p_start%"] >= 50)]
           .sort_values("value_H", ascending=False)
           .head(15)[["name", "team", "pos", "price", "xP_H", "value_H"]])
    out.append(("Best value overall (xP per £m)", val))
    dc = (df[(df["pos"].isin(["DEF", "MID"])) & (df["p_start%"] >= 55)]
          .sort_values("xP_defcon", ascending=False)
          .head(15)[["name", "team", "pos", "price", "DEFCON90", "xP_defcon", "xP_H"]])
    out.append(("Best DEFCON set-&-forget", dc))
    diff = (df[(df["own%"] <= C.DIFFERENTIAL_MAX_OWNERSHIP) & (df["p_start%"] >= 55)]
            .sort_values("xP_H", ascending=False)
            .head(15)[["name", "team", "pos", "own%", "xP_next", "xP_H"]])
    out.append((f"Best differentials (≤{int(C.DIFFERENTIAL_MAX_OWNERSHIP)}%)", diff))
    cap = (df[df["p_start%"] >= 60]
           .sort_values("xP_next", ascending=False)
           .head(12)[["name", "team", "pos", "own%", "xP_next"]])
    out.append(("Captaincy ranking (next GW)", cap))
    return out


def build_setpieces(df):
    sp = df[(df["pen"].notna()) | (df["fk"].notna()) | (df["ck"].notna())].copy()
    sp = sp.sort_values(["team", "pen", "fk", "ck"], na_position="last")
    return sp[["team", "name", "pos", "pen", "fk", "ck", "own%", "xP_H"]]


def build_chips(fixtures, team_ratings, next_event):
    events = FX.detect_double_blank(fixtures, team_ratings, next_event, 14)
    short = {tid: r["short"] for tid, r in team_ratings.items()}
    all_tids = set(team_ratings)
    rows = []
    for ev in sorted(events):
        counts = events[ev]
        doubles = [short[t] for t, c in counts.items() if c >= 2]
        playing = set(counts)
        blanks = [short[t] for t in all_tids - playing]
        tag = "Double GW" if doubles else ("Blank GW" if blanks else "Normal")
        rows.append({
            "GW": ev,
            "Type": tag,
            "Doubles(DBL)": ", ".join(sorted(doubles)) if doubles else "-",
            "Blanks(BLK)": ", ".join(sorted(blanks)) if blanks else "-",
        })
    return pd.DataFrame(rows)


def match_squad(df):
    rows, notes = [], []
    used = set()
    for name, hint in C.MY_SQUAD:
        cand = df[df["name"].str.lower() == name.lower()]
        if hint:
            h = cand[cand["team"] == hint]
            if len(h):
                cand = h
        cand = cand[~cand["id"].isin(used)]
        if len(cand) == 0:
            cand = df[df["name"].str.lower().str.contains(name.lower(), regex=False)]
            cand = cand[~cand["id"].isin(used)]
        if len(cand):
            row = cand.sort_values("min", ascending=False).iloc[0]
            used.add(row["id"])
            rows.append(row)
        else:
            notes.append(f"• Could not match '{name}' — check spelling in config.MY_SQUAD")
    sdf = pd.DataFrame(rows)
    return sdf, notes


def analyse_squad(sdf, df, notes):
    cols = ["name", "team", "pos", "price", "own%", "nailed",
            "xP_next", "xP_H", "status", "news"]
    view = sdf[cols].copy() if len(sdf) else pd.DataFrame(columns=cols)
    total_next = sdf["xP_next"].sum() if len(sdf) else 0
    cap_row = df[df["name"].str.lower() == C.MY_CAPTAIN.lower()]
    cap_xp = cap_row["xP_next"].max() if len(cap_row) else 0
    lines = []
    lines.append(f"VERDICT")
    lines.append(f"• Squad projected xP next GW (all 15, pre-captain): {total_next:.1f}")
    lines.append(f"• Captain {C.MY_CAPTAIN} adds ~{cap_xp:.1f} more (doubled).")
    # flags
    flags = sdf[sdf["status"] != "a"] if len(sdf) else sdf
    lines.append("FLAGS")
    if len(flags):
        for _, r in flags.iterrows():
            lines.append(f"• {r['name']} ({r['team']}) status '{r['status']}' — {r['news'] or 'monitor'}")
    else:
        lines.append("• No injury/availability flags in your squad.")
    # weakest links among likely starters
    lines.append("SUGGESTIONS")
    if len(sdf):
        starters = sdf[sdf["nailed"] >= 40].sort_values("xP_H")
        weak = starters.head(3)
        for _, r in weak.iterrows():
            better = df[(df["pos"] == r["pos"]) & (df["price"] <= r["price"] + 0.5) &
                        (df["xP_H"] > r["xP_H"]) & (df["p_start%"] >= 60)]
            better = better.sort_values("xP_H", ascending=False).head(3)
            opts = ", ".join(f"{b['name']}({b['team']} £{b['price']}, {b['xP_H']})"
                             for _, b in better.iterrows()) or "no clear upgrade in range"
            lines.append(f"• Weak link {r['name']} ({r['pos']}, xP_H {r['xP_H']}) → consider: {opts}")
    lines += notes
    return view, lines


def main():
    print("FPL ENGINE — refresh starting ...")
    boot = D.fetch_bootstrap()
    fixtures = D.fetch_fixtures()
    season = D.season_label(boot)
    cur_ev, next_ev, games_played = D.current_and_next_event(boot)
    next_event = (next_ev or cur_ev)["id"] if (next_ev or cur_ev) else 1
    print(f"  season {season} | next GW {next_event} | GWs played {games_played}")

    history = D.fetch_history(boot["elements"])

    print("  building team ratings ...")
    team_ratings, avg_att, avg_def = M.build_team_ratings(boot, games_played)
    upcoming = FX.team_upcoming(fixtures, team_ratings, avg_att, avg_def,
                                next_event, C.HORIZON)

    print("  scoring players ...")
    df = P.build_players_frame(boot, history, team_ratings, upcoming,
                               next_event, games_played)

    print("  building derived tables ...")
    teams_df = build_teams_df(team_ratings, upcoming, next_event)
    fixture_matrix, evlist = build_fixture_matrix(team_ratings, upcoming, next_event)
    watchlist_df = build_watchlist(df)
    rankings = build_rankings(df)
    setpiece_df = build_setpieces(df)
    chips_df = build_chips(fixtures, team_ratings, next_event)

    print("  running optimiser ...")
    chosen, status = OPT.optimise(df)
    optimiser = None
    if chosen:
        odf = pd.DataFrame(chosen)
        cost = odf["price"].sum()
        xi_xp = odf[odf["in_XI"]]["xP_H"].sum()
        cap = odf[odf["captain"]]["name"].iloc[0] if odf["captain"].any() else "-"
        odf_disp = odf.copy()
        odf_disp["role"] = odf_disp.apply(
            lambda r: "C" if r["captain"] else ("XI" if r["in_XI"] else "BENCH"), axis=1)
        optimiser = {"df": odf_disp[["role", "name", "team", "pos", "price",
                                     "own%", "xP_next", "xP_H"]],
                     "cost": cost, "xi_xp": xi_xp, "captain": cap, "status": status}

    print("  analysing your squad ...")
    sdf, mnotes = match_squad(df)
    my_view, my_notes = analyse_squad(sdf, df, mnotes)

    meta = {"season": season, "next_event": next_event,
            "games_played": games_played,
            "updated": dt.datetime.now().strftime("%Y-%m-%d %H:%M")}

    ctx = {"df": df, "teams_df": teams_df, "fixture_matrix": fixture_matrix,
           "tracker_evlist": evlist, "watchlist_df": watchlist_df,
           "rankings": rankings, "optimiser": optimiser,
           "setpiece_df": setpiece_df, "chips_df": chips_df,
           "my_squad_df": my_view, "my_squad_notes": my_notes, "meta": meta}

    print("  writing workbook ...")
    try:
        path = W.build_workbook(ctx)
    except Exception as e:
        path = f"(workbook skipped: {e})"
        print(f"  ! workbook write failed: {e}")

    # ---- per-GW projection for EVERY player (powers client-side per-user calc) ----
    print("  building season-long projection ...")
    rates_by_id, event_xp, meta_by_id, _ = PROJ.build_projection(
        boot, history, team_ratings, avg_att, avg_def, fixtures, next_event)
    field_cum_now = sum(e.get("average_entry_score") or 0
                        for e in boot["events"] if e.get("finished"))

    # optional: log the default team's rank so we can eyeball each run
    if C.MY_ENTRY_ID:
        entry = D.fetch_entry(C.MY_ENTRY_ID)
        ehist = D.fetch_entry_history(C.MY_ENTRY_ID)
        if entry:
            rr = RANKS.project(boot, entry, ehist, event_xp, meta_by_id, next_event)
            print(f"    default entry {C.MY_ENTRY_ID}: rank now "
                  f"{rr['entry']['overall_rank']:,} -> GW38 p50 "
                  f"{rr['summary']['rank_gw38_p50']:,}")

    web_meta = {"season": season, "next_event": next_event,
                "games_played": games_played,
                "updated_iso": dt.datetime.now(dt.timezone.utc).isoformat(),
                "updated": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
                "total_players": boot.get("total_players")}
    model_cfg = {
        "total_players": boot.get("total_players"),
        "field_cum_now": field_cum_now,
        "field_avg_per_gw": C.FIELD_AVG_PER_GW,
        "sd_growth_exp": C.SD_GROWTH_EXP,
        "edge_damping": C.EDGE_DAMPING,
        "per_gw_player_sd": C.PER_GW_PLAYER_SD,
        "mc_sims": C.MC_SIMS,
        "horizon": C.HORIZON,
        "max_per_club": C.MAX_PER_CLUB,
        "default_entry": C.MY_ENTRY_ID,
    }
    print("  writing web model JSON ...")
    wdir = WEB.write_model(ctx, event_xp, meta_by_id, df, web_meta, model_cfg,
                           next_event)

    print(f"DONE -> {path}")
    print(f"  web data -> {wdir}")
    print(f"  players scored: {len(df)} | teams: {len(teams_df)} | "
          f"optimiser: {status if chosen else 'n/a'}")


if __name__ == "__main__":
    sys.exit(main())
