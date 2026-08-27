"""
Data layer: fetch from the official FPL API with caching.

- bootstrap-static & fixtures are refreshed every run (they change weekly).
- per-player history_past (last-season xG / DEFCON) is immutable, so it is
  cached permanently in data/history_cache.json and only fetched for players
  we haven't seen before. First run pulls ~600 players (~1-2 min); later runs
  are near-instant.
"""
import json
import time
import sys
import requests

from . import config as C


def _get(url):
    r = requests.get(url, headers=C.HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()


def fetch_bootstrap(use_cache_if_offline=True):
    try:
        data = _get(C.BOOTSTRAP_URL)
        (C.DATA_DIR / "bootstrap_static.json").write_text(
            json.dumps(data), encoding="utf-8")
        return data
    except Exception as e:
        cache = C.DATA_DIR / "bootstrap_static.json"
        if use_cache_if_offline and cache.exists():
            print(f"  ! bootstrap fetch failed ({e}); using cached copy")
            return json.loads(cache.read_text(encoding="utf-8"))
        raise


def fetch_fixtures(use_cache_if_offline=True):
    try:
        data = _get(C.FIXTURES_URL)
        (C.DATA_DIR / "fixtures.json").write_text(
            json.dumps(data), encoding="utf-8")
        return data
    except Exception as e:
        cache = C.DATA_DIR / "fixtures.json"
        if use_cache_if_offline and cache.exists():
            print(f"  ! fixtures fetch failed ({e}); using cached copy")
            return json.loads(cache.read_text(encoding="utf-8"))
        raise


def _load_history_cache():
    f = C.DATA_DIR / "history_cache.json"
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    return {}


def _save_history_cache(cache):
    (C.DATA_DIR / "history_cache.json").write_text(
        json.dumps(cache), encoding="utf-8")


def fetch_history(elements, force=False):
    """
    Return {player_code: last_season_history_past_row_or_None}.

    Keyed by the stable `code` (survives across seasons / id reshuffles).
    Only the most recent completed season in history_past is kept.
    """
    cache = {} if force else _load_history_cache()
    codes_needed = [e["code"] for e in elements if str(e["code"]) not in cache]
    total = len(codes_needed)
    if total:
        print(f"  fetching last-season history for {total} new players "
              f"(cached: {len(cache)}) ...")
    code_to_id = {e["code"]: e["id"] for e in elements}
    done = 0
    for code in codes_needed:
        pid = code_to_id[code]
        try:
            js = _get(C.ELEMENT_SUMMARY_URL.format(pid=pid))
            past = js.get("history_past", [])
            cache[str(code)] = past[-1] if past else None
        except Exception:
            cache[str(code)] = None
        done += 1
        if done % 50 == 0 or done == total:
            print(f"    ... {done}/{total}")
            _save_history_cache(cache)
        time.sleep(C.HISTORY_FETCH_DELAY)
    _save_history_cache(cache)
    return cache


def fetch_entry(entry_id):
    """Manager summary: name, overall points/rank, current event."""
    try:
        return _get(f"{C.BASE}/entry/{entry_id}/")
    except Exception as e:
        print(f"  ! entry fetch failed ({e})")
        return None


def fetch_entry_history(entry_id):
    """Per-GW history (points, overall_rank, value, bank) + chips used."""
    try:
        return _get(f"{C.BASE}/entry/{entry_id}/history/")
    except Exception as e:
        print(f"  ! entry history fetch failed ({e})")
        return None


def fetch_picks(entry_id, event):
    """The manager's actual squad for a given (finished/deadline-passed) GW."""
    try:
        return _get(f"{C.BASE}/entry/{entry_id}/event/{event}/picks/")
    except Exception:
        return None


def fetch_live(event):
    """Live per-player points for an in-progress GW (used by the web proxy too)."""
    try:
        return _get(f"{C.BASE}/event/{event}/live/")
    except Exception:
        return None


def season_label(bootstrap):
    """Best-effort label of the current season, e.g. '2026/27'."""
    # Derive from the first event's deadline year if available.
    try:
        yr = int(bootstrap["events"][0]["deadline_time"][:4])
        return f"{yr}/{str(yr + 1)[-2:]}"
    except Exception:
        return "current"


def current_and_next_event(bootstrap):
    cur = nxt = None
    for ev in bootstrap["events"]:
        if ev.get("is_current"):
            cur = ev
        if ev.get("is_next"):
            nxt = ev
    finished = sum(1 for ev in bootstrap["events"] if ev.get("finished"))
    return cur, nxt, finished
