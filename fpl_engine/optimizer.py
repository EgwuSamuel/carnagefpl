"""
Squad optimiser: pick the best legal 15 (£100m, 2/5/5/3, max 3 per club) that
maximises expected points over the horizon, choosing a realistic starting XI
(bench treated as cheaper enablers) and the best captain for the next GW.
"""
import pulp

from . import config as C


def optimise(df, budget=None):
    budget = budget or C.BUDGET
    pool = df.copy()
    # candidate pool: everything priced; the model down-weights non-starters
    pool = pool[pool["price"] > 0].reset_index(drop=True)

    idx = list(pool.index)
    xph = {i: float(pool.at[i, "xP_H"]) for i in idx}
    xpn = {i: float(pool.at[i, "xP_next"]) for i in idx}
    price = {i: float(pool.at[i, "price"]) for i in idx}
    pos = {i: pool.at[i, "pos"] for i in idx}
    club = {i: pool.at[i, "team"] for i in idx}

    prob = pulp.LpProblem("fpl_squad", pulp.LpMaximize)
    x = pulp.LpVariable.dicts("squad", idx, cat="Binary")   # in 15
    y = pulp.LpVariable.dicts("xi", idx, cat="Binary")      # in starting XI
    c = pulp.LpVariable.dicts("cap", idx, cat="Binary")     # captain

    # objective: XI points (horizon) + small credit for bench + captain (next GW)
    prob += (
        pulp.lpSum(y[i] * xph[i] for i in idx)
        + 0.15 * pulp.lpSum((x[i] - y[i]) * xph[i] for i in idx)
        + pulp.lpSum(c[i] * xpn[i] for i in idx)
    )

    # squad structure
    for p, n in C.SQUAD_STRUCTURE.items():
        prob += pulp.lpSum(x[i] for i in idx if pos[i] == p) == n
    prob += pulp.lpSum(x[i] for i in idx) == 15
    prob += pulp.lpSum(price[i] * x[i] for i in idx) <= budget

    # max per club
    for cl in set(club.values()):
        prob += pulp.lpSum(x[i] for i in idx if club[i] == cl) <= C.MAX_PER_CLUB

    # starting XI: 11 players, valid formation ranges, subset of squad
    prob += pulp.lpSum(y[i] for i in idx) == 11
    for i in idx:
        prob += y[i] <= x[i]
        prob += c[i] <= y[i]
    prob += pulp.lpSum(y[i] for i in idx if pos[i] == "GKP") == 1
    prob += pulp.lpSum(y[i] for i in idx if pos[i] == "DEF") >= 3
    prob += pulp.lpSum(y[i] for i in idx if pos[i] == "DEF") <= 5
    prob += pulp.lpSum(y[i] for i in idx if pos[i] == "MID") >= 2
    prob += pulp.lpSum(y[i] for i in idx if pos[i] == "MID") <= 5
    prob += pulp.lpSum(y[i] for i in idx if pos[i] == "FWD") >= 1
    prob += pulp.lpSum(y[i] for i in idx if pos[i] == "FWD") <= 3
    prob += pulp.lpSum(c[i] for i in idx) == 1

    prob.solve(pulp.PULP_CBC_CMD(msg=0))

    status = pulp.LpStatus[prob.status]
    if status != "Optimal":
        return None, status

    chosen = []
    for i in idx:
        if x[i].value() and x[i].value() > 0.5:
            chosen.append({
                "name": pool.at[i, "name"],
                "team": club[i],
                "pos": pos[i],
                "price": price[i],
                "own%": pool.at[i, "own%"],
                "xP_next": pool.at[i, "xP_next"],
                "xP_H": pool.at[i, "xP_H"],
                "in_XI": bool(y[i].value() and y[i].value() > 0.5),
                "captain": bool(c[i].value() and c[i].value() > 0.5),
            })
    # order: XI first (by pos then xP), then bench
    order = {"GKP": 0, "DEF": 1, "MID": 2, "FWD": 3}
    chosen.sort(key=lambda r: (not r["in_XI"], order[r["pos"]], -r["xP_H"]))
    return chosen, status
