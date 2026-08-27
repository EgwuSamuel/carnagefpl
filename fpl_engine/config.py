"""
Central configuration for the FPL Engine.

Everything the model 'believes' lives here as a tunable constant, so you can
adjust the engine's behaviour without touching the maths. Edit, re-run
`python fpl_refresh.py`, and every number in the workbook updates.
"""
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
OUTPUT_XLSX = ROOT / "FPL_Master.xlsx"
DATA_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# FPL API
# ---------------------------------------------------------------------------
BASE = "https://fantasy.premierleague.com/api"
HEADERS = {"User-Agent": "Mozilla/5.0 (FPL-Engine research tool)"}
BOOTSTRAP_URL = f"{BASE}/bootstrap-static/"
FIXTURES_URL = f"{BASE}/fixtures/"
ELEMENT_SUMMARY_URL = BASE + "/element-summary/{pid}/"

# Polite delay between the per-player history calls (seconds)
HISTORY_FETCH_DELAY = 0.03

# ---------------------------------------------------------------------------
# Position encoding (FPL element_type)
# ---------------------------------------------------------------------------
POS = {1: "GKP", 2: "DEF", 3: "MID", 4: "FWD"}

# Points per goal, by position
GOAL_PTS = {"GKP": 6, "DEF": 6, "MID": 5, "FWD": 4}
ASSIST_PTS = 3
# Points for a clean sheet, by position
CS_PTS = {"GKP": 4, "DEF": 4, "MID": 1, "FWD": 0}
# Defensive Contribution ("DEFCON") points and the action threshold per position
DEFCON_PTS = 2
DEFCON_THRESHOLD = {"GKP": 99, "DEF": 10, "MID": 12, "FWD": 12}  # GKP effectively n/a

# ---------------------------------------------------------------------------
# Model weights & priors
# ---------------------------------------------------------------------------
# How fast we trust *this* season's data vs last season's per-90 rates.
# weight_current = min(current_minutes / RATE_FULL_TRUST_MINUTES, RATE_MAX_CURRENT_WEIGHT)
RATE_FULL_TRUST_MINUTES = 540          # ~6 full matches to (nearly) fully trust current form
RATE_MAX_CURRENT_WEIGHT = 0.80         # never fully abandon the last-season prior

# Team strength: blend of FPL's 1-5 overall rating (a preseason prior that also
# covers promoted teams) and season-to-date xG. Current xG earns trust with games.
TEAM_FULL_TRUST_GAMES = 6
TEAM_MAX_CURRENT_WEIGHT = 0.80

# League baselines (goals per team per game). Used to normalise fixture strength.
LEAGUE_AVG_GOALS = 1.45

# Map FPL strength_overall (1..5) -> a prior for goals scored / conceded per game
# vs an average opponent. Strong attack scores more; strong defence concedes less.
def prior_attack(strength):      # strength 1..5
    return 0.55 + 0.26 * strength          # 1->0.81 ... 5->1.85

def prior_defence(strength):     # goals conceded vs avg opponent
    return 2.35 - 0.28 * strength          # 1->2.07 ... 5->0.95

# Home/away adjustment applied to expected goals.
HOME_ATTACK_MULT = 1.10
AWAY_ATTACK_MULT = 0.92
HOME_DEFENCE_MULT = 0.92   # concede fewer at home
AWAY_DEFENCE_MULT = 1.10

# Minutes model
STARTER_MINUTES = 88       # expected minutes for a nailed starter
CAMEO_MINUTES = 22         # expected minutes for a rotation/sub player when they feature

# Horizon (number of upcoming gameweeks) for the medium-term xP column & optimiser
HORIZON = 5

# Differential threshold (selected_by_percent below this = differential)
DIFFERENTIAL_MAX_OWNERSHIP = 12.0

# ---------------------------------------------------------------------------
# Squad budget / structure (for the optimiser)
# ---------------------------------------------------------------------------
BUDGET = 100.0
SQUAD_STRUCTURE = {"GKP": 2, "DEF": 5, "MID": 5, "FWD": 3}
MAX_PER_CLUB = 3
# Valid outfield formations (GK is always 1); used to pick the best XI
FORMATIONS = [
    (3, 4, 3), (3, 5, 2), (4, 4, 2), (4, 3, 3),
    (4, 5, 1), (5, 4, 1), (5, 3, 2), (3, 3, 4),
]

# ---------------------------------------------------------------------------
# YOUR current squad — matched by web_name (case-insensitive), with an optional
# team short-code hint to disambiguate common surnames. Edit this to match your
# real team, then re-run to refresh the "My Squad" analysis.
# Format: (web_name, team_short_code_hint or None)
# ---------------------------------------------------------------------------
MY_SQUAD = [
    ("Kinsky", "TOT"),
    ("Verbruggen", "BHA"),
    ("Rodon", "LEE"),
    ("Maguire", "MUN"),
    ("Calafiori", "ARS"),
    ("Diop", None),
    ("Ajer", "BRE"),
    ("Tzolis", None),
    ("Mbeumo", "MUN"),
    ("Szoboszlai", "LIV"),
    ("B.Fernandes", "MUN"),
    ("Gomez", None),
    ("João Pedro", "CHE"),
    ("Haaland", "MCI"),
    ("Calvert-Lewin", None),
]
MY_CAPTAIN = "Haaland"
MY_VICE = "Kinsky"

# ---------------------------------------------------------------------------
# Your FPL manager (entry) id — from your team URL /entry/<ID>/event/... .
# When set, the engine pulls your REAL squad, points and rank from the API
# (overriding the MY_SQUAD guess above) and powers rank projection.
# ---------------------------------------------------------------------------
MY_ENTRY_ID = 8611170

# Rank-projection settings
FREE_TRANSFERS_ASSUMED = 1        # FTs available now (API can't expose exact balance)
FIELD_AVG_PER_GW = 52.0           # assumed average manager score for future GWs
MC_SIMS = 2000                    # Monte-Carlo simulations for the rank band
PER_GW_PLAYER_SD = 9.0            # spread of YOUR weekly score around its mean
EDGE_DAMPING = 0.45               # damp model edge vs template (model is uncertain;
                                  # managers also converge to template via transfers)
SD_GROWTH_EXP = 0.5               # how fast cross-manager spread grows (0.5=sqrt)

# Where the web dashboard reads its JSON from
WEB_DATA_DIR = ROOT / "web" / "public" / "data"
