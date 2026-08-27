"""
Fixture processing: build each team's upcoming schedule, a custom xG-based
Fixture Difficulty Rating (FDR), and detect double/blank gameweeks.
"""
from . import model as M


def team_upcoming(fixtures, team_ratings, avg_att, avg_def, next_event, horizon):
    """
    Returns {team_id: [ {event, opp_id, opp_short, is_home, opp,
                         xgc(our exp goals conceded), xgf_mult,
                         fdr_att, fdr_def} ... ]} for events >= next_event.
    """
    out = {tid: [] for tid in team_ratings}
    if next_event is None:
        return out
    last_event = next_event + horizon + 6  # look a bit beyond horizon for the tracker
    for fx in fixtures:
        ev = fx.get("event")
        if ev is None or ev < next_event or ev > last_event:
            continue
        h, a = fx["team_h"], fx["team_a"]
        if h not in team_ratings or a not in team_ratings:
            continue
        for tid, opp, is_home in ((h, a, True), (a, h, False)):
            tr, orr = team_ratings[tid], team_ratings[opp]
            xgc = M.expected_goals_conceded(tr, orr, is_home, avg_att)
            xgf_mult = M.attack_fixture_mult(orr, is_home, avg_def)
            out[tid].append({
                "event": ev,
                "opp_id": opp,
                "opp_short": orr["short"],
                "is_home": is_home,
                "label": f"{orr['short']} ({'H' if is_home else 'A'})",
                "xgc": xgc,                 # lower = better for clean sheets
                "xgf_mult": xgf_mult,       # higher = better for attackers
                "fdr_att": fdr_from_mult(xgf_mult),
                "fdr_def": fdr_from_xgc(xgc),
            })
    for tid in out:
        out[tid].sort(key=lambda r: (r["event"], r["opp_short"]))
    return out


def fdr_from_xgc(xgc):
    """Map expected goals conceded -> 1 (easy) .. 5 (hard) for defenders/GK."""
    if xgc < 0.85:
        return 1
    if xgc < 1.15:
        return 2
    if xgc < 1.45:
        return 3
    if xgc < 1.85:
        return 4
    return 5


def fdr_from_mult(mult):
    """Map attacking multiplier -> 1 (easy) .. 5 (hard) for attackers."""
    if mult > 1.30:
        return 1
    if mult > 1.10:
        return 2
    if mult > 0.92:
        return 3
    if mult > 0.75:
        return 4
    return 5


def combined_fdr(row):
    """Overall fixture difficulty (average of att & def perspective)."""
    return round((row["fdr_att"] + row["fdr_def"]) / 2.0, 1)


def detect_double_blank(fixtures, team_ratings, next_event, num_events=12):
    """
    Returns {event: {team_id: count}} of fixtures per team per event, so the
    tracker can flag doubles (2+) and blanks (0).
    """
    events = {}
    for fx in fixtures:
        ev = fx.get("event")
        if ev is None or ev < next_event or ev > next_event + num_events:
            continue
        for tid in (fx["team_h"], fx["team_a"]):
            events.setdefault(ev, {}).setdefault(tid, 0)
            events[ev][tid] += 1
    return events
