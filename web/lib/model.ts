// Client-side port of the Python projection & transfer maths, so any manager's
// ID can be projected in the browser from the published team-agnostic model.json.

export function phi(x: number) {
  // standard normal CDF via erf approximation (Abramowitz & Stegun 7.1.26)
  const t = 1 / (1 + 0.3275911 * Math.abs(x) / Math.SQRT2);
  const y =
    1 -
    ((((1.061405429 * t - 1.453152027) * t + 1.421413741) * t - 0.284496736) * t +
      0.254829592) *
      t *
      Math.exp((-x * x) / 2);
  return x >= 0 ? 0.5 * (1 + y) : 0.5 * (1 - y);
}

export function invPhi(p: number) {
  p = Math.min(Math.max(p, 1e-9), 1 - 1e-9);
  const a = [-39.69683028665376, 220.9460984245205, -275.9285104469687, 138.357751867269, -30.66479806614716, 2.506628277459239];
  const b = [-54.47609879822406, 161.5858368580409, -155.6989798598866, 66.80131188771972, -13.28068155288572];
  const c = [-0.007784894002430293, -0.3223964580411365, -2.400758277161838, -2.549732539343734, 4.374664141464968, 2.938163982698783];
  const d = [0.007784695709041462, 0.3224671290700398, 2.445134137142996, 3.754408661907416];
  const plow = 0.02425, phigh = 1 - plow;
  if (p < plow) {
    const q = Math.sqrt(-2 * Math.log(p));
    return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) /
      ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1);
  }
  if (p > phigh) {
    const q = Math.sqrt(-2 * Math.log(1 - p));
    return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) /
      ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1);
  }
  const q = p - 0.5, r = q * q;
  return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q /
    (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1);
}

function gauss(mean: number, sd: number) {
  const u = Math.random() || 1e-9, v = Math.random() || 1e-9;
  return mean + sd * Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
}

const xpOf = (exp: any, id: number, ev: number) => exp[String(id)]?.[String(ev)] ?? 0;

function bestXi(players: { id: number; pos: string; xp: number }[]) {
  const byPos = (p: string) => players.filter((x) => x.pos === p).sort((a, b) => b.xp - a.xp);
  const gk = byPos("GKP"), de = byPos("DEF"), mi = byPos("MID"), fw = byPos("FWD");
  let best: any = null, bestXp = -1;
  for (let d = 3; d <= 5; d++)
    for (let m = 2; m <= 5; m++)
      for (let f = 1; f <= 3; f++) {
        if (d + m + f !== 10) continue;
        if (de.length < d || mi.length < m || fw.length < f || gk.length < 1) continue;
        const xi = [gk[0], ...de.slice(0, d), ...mi.slice(0, m), ...fw.slice(0, f)];
        const s = xi.reduce((a, x) => a + x.xp, 0);
        if (s > bestXp) { bestXp = s; best = xi; }
      }
  return best || [gk[0], ...de, ...mi, ...fw].filter(Boolean);
}

export function teamGwPoints(
  pickIds: number[], exp: any, byId: Map<number, any>, ev: number,
  captainId: number | null, benchBoost = false
) {
  const players = pickIds
    .filter((id) => byId.has(id))
    .map((id) => ({ id, pos: byId.get(id).pos, xp: xpOf(exp, id, ev) }));
  const chosen = benchBoost ? players : bestXi(players);
  let total = chosen.reduce((a, x) => a + x.xp, 0);
  const inXi = new Set(chosen.map((x) => x.id));
  let capXp = 0;
  if (captainId && inXi.has(captainId)) capXp = xpOf(exp, captainId, ev);
  else if (chosen.length) capXp = Math.max(...chosen.map((x) => x.xp));
  return total + capXp;
}

function fieldTeamXp(ev: number, players: any[], exp: any) {
  const byPos: any = { GKP: [], DEF: [], MID: [], FWD: [] };
  for (const p of players) byPos[p.pos]?.push({ own: p["own%"], xp: xpOf(exp, p.id, ev) });
  for (const k of Object.keys(byPos)) byPos[k].sort((a: any, b: any) => b.own - a.own);
  const xi = [...byPos.GKP.slice(0, 1), ...byPos.DEF.slice(0, 3), ...byPos.MID.slice(0, 4), ...byPos.FWD.slice(0, 3)];
  const total = xi.reduce((a, x) => a + x.xp, 0);
  const atk = [...byPos.MID.slice(0, 4), ...byPos.FWD.slice(0, 3)];
  const cap = atk.length ? atk.reduce((m, x) => (x.own > m.own ? x : m)).xp : 0;
  return total + cap;
}

export function projectRank(model: any, entry: any, history: any, pickIds: number[], captainId: number | null) {
  const cfg = model.config;
  const N = cfg.total_players;
  const cur = history?.current || [];
  const gamesPlayed = cur.length || 1;
  const nextEvent = model.meta.next_event;
  const events: number[] = model.events.filter((e: number) => e >= nextEvent);
  const totalNow = cur.length ? cur[cur.length - 1].total_points : entry?.summary_overall_points || 0;
  const rankNow = cur.length ? cur[cur.length - 1].overall_rank : entry?.summary_overall_rank || N / 2;
  const teamValue = cur.length ? cur[cur.length - 1].value / 10 : 100;
  const bank = cur.length ? cur[cur.length - 1].bank / 10 : 0;
  const fieldCumNow = cfg.field_cum_now;

  const zNow = invPhi(1 - rankNow / N);
  const sdCumNow = zNow > 0.05 ? Math.max((totalNow - fieldCumNow) / zNow, 8) : 30;
  const sdCum = (el: number) => sdCumNow * Math.pow(el / Math.max(gamesPlayed, 1), cfg.sd_growth_exp);

  const byId = new Map<number, any>(model.players.map((p: any) => [p.id, p]));
  const base: any = {}, yourModel: any = {}, fieldMean: any = {}, yourMean: any = {};
  for (const e of events) base[e] = fieldTeamXp(e, model.players, model.event_xp);
  const scale = Math.min(Math.max(cfg.field_avg_per_gw / (base[nextEvent] || 1), 0.6), 1.8);
  for (const e of events) {
    yourModel[e] = pickIds.length ? teamGwPoints(pickIds, model.event_xp, byId, e, captainId) : base[e];
    fieldMean[e] = base[e] * scale;
    yourMean[e] = fieldMean[e] + (yourModel[e] - base[e]) * scale * cfg.edge_damping;
  }

  const proj: any[] = [];
  let ytot = totalNow, ftot = fieldCumNow, el = gamesPlayed;
  const fieldCumPath: any = {};
  for (const e of events) {
    el += 1; ytot += yourMean[e]; ftot += fieldMean[e]; fieldCumPath[e] = ftot;
    const z = (ytot - ftot) / sdCum(el);
    proj.push({ event: e, your_pts: +yourMean[e].toFixed(1), cum_your_pts: +ytot.toFixed(1), rank_p50: Math.max(1, Math.min(Math.round(N * (1 - phi(z))), N)) });
  }

  // Monte-Carlo band
  const samples: Record<number, number[]> = {};
  for (const e of events) samples[e] = [];
  const sims = Math.min(cfg.mc_sims || 1500, 1500);
  for (let s = 0; s < sims; s++) {
    let y = totalNow, ee = gamesPlayed;
    for (const e of events) {
      ee += 1; y += gauss(yourMean[e], cfg.per_gw_player_sd);
      const z = (y - fieldCumPath[e]) / sdCum(ee);
      samples[e].push(N * (1 - phi(z)));
    }
  }
  for (const row of proj) {
    const s = samples[row.event].sort((a, b) => a - b);
    row.rank_p10 = Math.max(1, Math.round(s[Math.floor(0.1 * s.length)]));
    row.rank_p90 = Math.min(N, Math.round(s[Math.floor(0.9 * s.length)]));
  }

  const p5 = proj.find((r) => r.event === nextEvent + 4) || proj[Math.min(4, proj.length - 1)];
  const p38 = proj[proj.length - 1];
  return {
    entry: { id: entry?.id, name: entry?.name, player: `${entry?.player_first_name || ""} ${entry?.player_last_name || ""}`.trim(), overall_points: totalNow, overall_rank: rankNow, current_event: gamesPlayed, team_value: +teamValue.toFixed(1), bank: +bank.toFixed(1), total_players: N },
    chips_used: (history?.chips || []).map((c: any) => ({ name: c.name, event: c.event })),
    projection: proj,
    summary: {
      rank_now: rankNow,
      rank_gw5_p50: p5?.rank_p50, rank_gw5_p10: p5?.rank_p10, rank_gw5_p90: p5?.rank_p90,
      rank_gw38_p50: p38?.rank_p50, rank_gw38_p10: p38?.rank_p10, rank_gw38_p90: p38?.rank_p90,
      proj_final_points: p38?.cum_your_pts,
    },
    _bank: bank,
  };
}

export function planTransfers(model: any, pickIds: number[], bank: number) {
  const cfg = model.config;
  const nextEvent = model.meta.next_event;
  const end = nextEvent + cfg.horizon - 1;
  const byId = new Map<number, any>(model.players.map((p: any) => [p.id, p]));
  const hz = (id: number) => { let s = 0; for (let e = nextEvent; e <= end; e++) s += xpOf(model.event_xp, id, e); return s; };
  const idsByPos: any = { GKP: [], DEF: [], MID: [], FWD: [] };
  for (const p of model.players) idsByPos[p.pos]?.push(p.id);

  const bestSwaps = (squad: number[], bk: number, start: number, top: number) => {
    const set = new Set(squad);
    const counts: any = {};
    for (const id of squad) { const t = byId.get(id)?.team; counts[t] = (counts[t] || 0) + 1; }
    const out: any[] = [];
    for (const o of squad) {
      const mo = byId.get(o); if (!mo) continue;
      const oxp = (() => { let s = 0; for (let e = start; e <= end; e++) s += xpOf(model.event_xp, o, e); return s; })();
      const budget = bk + mo.price;
      for (const cand of idsByPos[mo.pos]) {
        if (set.has(cand)) continue;
        const mc = byId.get(cand);
        if (mc.price > budget + 1e-6) continue;
        if (mc.team !== mo.team && (counts[mc.team] || 0) + 1 > cfg.max_per_club) continue;
        if (mc.p_start < 0.35) continue;
        let cxp = 0; for (let e = start; e <= end; e++) cxp += xpOf(model.event_xp, cand, e);
        const gain = cxp - oxp;
        if (gain <= 0.05) continue;
        out.push({ out: mo.name, out_team: mo.team, out_pos: mo.pos, out_price: mo.price, in: mc.name, in_team: mc.team, in_price: mc.price, in_own: mc["own%"], gain: +gain.toFixed(2), gain_after_hit: +(gain - 4).toFixed(2), out_id: o, in_id: cand });
      }
    }
    out.sort((a, b) => b.gain - a.gain);
    return out.slice(0, top);
  };

  if (!pickIds.length) return { available: false, note: "No squad found for that ID yet." };
  const singles = bestSwaps(pickIds, bank, nextEvent, 10);
  let sq = [...pickIds], bk = bank;
  const plan: any[] = [];
  for (let wk = 0; wk < cfg.horizon; wk++) {
    const gw = nextEvent + wk;
    const best = bestSwaps(sq, bk, gw, 1);
    if (best.length && best[0].gain > 0.3) {
      const s = best[0];
      sq = sq.filter((x) => x !== s.out_id); sq.push(s.in_id);
      bk = +(bk + s.out_price - s.in_price).toFixed(1);
      plan.push({ gw, out: s.out, in: s.in, gain: s.gain, bank_after: bk });
    } else plan.push({ gw, out: "-", in: "hold (no clear gain)", gain: 0, bank_after: bk });
  }
  return { available: true, bank: +bank.toFixed(1), free_transfers: 1, horizon: cfg.horizon, single_transfers: singles, plan_5gw: plan, note: "Sell prices approximated as current price; verify in the FPL app." };
}

export function buildSquad(model: any, picks: any) {
  if (!picks?.picks) return { squad: [], captainId: null };
  const byId = new Map<number, any>(model.players.map((p: any) => [p.id, p]));
  const captainId = picks.picks.find((p: any) => p.is_captain)?.element ?? null;
  const order: any = { GKP: 0, DEF: 1, MID: 2, FWD: 3 };
  const squad = picks.picks
    .map((pk: any) => {
      const r = byId.get(pk.element);
      if (!r) return null;
      return { id: r.id, name: r.name, team: r.team, pos: r.pos, price: r.price, own: r["own%"], nailed: r.nailed, xP_next: r.xP_next, xP_H: r.xP_H, status: r.status, news: r.news || "", is_captain: pk.element === captainId };
    })
    .filter(Boolean)
    .sort((a: any, b: any) => order[a.pos] - order[b.pos] || b.xP_H - a.xP_H);
  return { squad, captainId };
}
