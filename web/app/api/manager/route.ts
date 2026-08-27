import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";
export const revalidate = 0;

const BASE = "https://fantasy.premierleague.com/api";
const H = { headers: { "User-Agent": "Mozilla/5.0 (carnagefpl)" }, cache: "no-store" as const };

// Proxy a manager's public data: summary, GW history, and latest squad picks.
export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const id = (searchParams.get("id") || "").trim();
  if (!/^\d+$/.test(id))
    return NextResponse.json({ error: "Enter a numeric FPL ID." }, { status: 400 });

  try {
    const [entryRes, histRes] = await Promise.all([
      fetch(`${BASE}/entry/${id}/`, H),
      fetch(`${BASE}/entry/${id}/history/`, H),
    ]);
    if (!entryRes.ok)
      return NextResponse.json({ error: "No manager found with that ID." }, { status: 404 });
    const entry = await entryRes.json();
    const history = histRes.ok ? await histRes.json() : { current: [], chips: [] };

    // latest gameweek with a saved squad
    const cur = history.current || [];
    const lastEvent = cur.length ? cur[cur.length - 1].event : 1;
    let picks: any = null;
    for (let ev = lastEvent; ev >= 1 && !picks; ev--) {
      const r = await fetch(`${BASE}/entry/${id}/event/${ev}/picks/`, H);
      if (r.ok) {
        const p = await r.json();
        if (p?.picks?.length) picks = p;
      }
    }
    return NextResponse.json({ entry, history, picks });
  } catch {
    return NextResponse.json({ error: "FPL API unavailable, try again." }, { status: 502 });
  }
}
