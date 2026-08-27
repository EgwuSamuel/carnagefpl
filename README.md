# Carnage FPL 🏆

A self-contained Fantasy Premier League decision engine **+ a live web dashboard**.
It pulls the official FPL API, blends this-season and last-season expected goals
(xG/xA/xGC) and **Defensive Contribution (DEFCON)** data, runs an **Expected
Points (xP)** model, a squad **optimiser**, a **rank projection** (to GW38) and a
**transfer planner** — then publishes it all to an auto-updating dashboard.

Anyone can enter their **FPL Team ID** and get their own projection.

## Two parts

| Part | What it is |
|---|---|
| `fpl_engine/` + `fpl_refresh.py` | Python engine → `FPL_Master.xlsx` (11-tab workbook) **and** `web/public/data/model.json` |
| `web/` | Next.js dashboard (deployed on Vercel) that reads `model.json` and computes any manager's rank + transfers client-side |

## Run the engine locally

```bash
pip install -r requirements.txt
python fpl_refresh.py
```

First run caches ~600 players' last-season history (immutable) so later runs take seconds.

## Run the dashboard locally

```bash
cd web
npm install
npm run dev        # http://localhost:3000
```

## The model (six routes to points)

Every player is scored on all six ways FPL awards points, combined into one `xP`:
goals/assists (xG/xA × fixture), clean sheets (Poisson on team xGC), saves,
bonus, **DEFCON** (Poisson tail on defensive actions vs the 10/12 threshold), and
minutes (availability × start-rate). Rates blend current + last season, weighting
current form more as games accumulate; players lacking history regress to
positional priors.

**Rank projection** calibrates the field's spread from your real overall rank,
measures your squad against the ownership template, and projects each GW to GW38
with a Monte-Carlo confidence band. **Transfer planner** ranks every legal swap by
expected points gained over the next 5 GWs (with hit break-even) and suggests a
5-week path.

All tunables live in `fpl_engine/config.py`.

## Auto-updates

`.github/workflows/refresh.yml` runs the engine **hourly** (GitHub Actions),
recomputes `model.json`, and commits it — which triggers a Vercel redeploy. The
dashboard also computes each visitor's team live from the FPL API on every visit,
so your rank/points are always current between refreshes.

## Deploy to Vercel

1. Push this repo to GitHub (done: `EgwuSamuel/carnagefpl`).
2. At [vercel.com](https://vercel.com) → **Add New → Project** → import `carnagefpl`.
3. Set **Root Directory = `web`**. Framework auto-detects as Next.js.
4. **Deploy.** You get `carnagefpl.vercel.app`.

## Data source

100% official FPL API — no scraping, no keys, no login. Public manager endpoints
power the per-user projection; last-season xG/DEFCON come from FPL's own
`history_past` records.
