import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";
export const revalidate = 0;

// Proxy the FPL live-scoring endpoint for an in-progress gameweek.
// Returns a compact { id: points } map so the dashboard can tick up live.
export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const event = searchParams.get("event");
  if (!event) return NextResponse.json({ error: "missing event" }, { status: 400 });
  try {
    const res = await fetch(
      `https://fantasy.premierleague.com/api/event/${event}/live/`,
      { headers: { "User-Agent": "Mozilla/5.0 (carnagefpl)" }, cache: "no-store" }
    );
    if (!res.ok) return NextResponse.json({ event, points: {} });
    const data = await res.json();
    const points: Record<number, number> = {};
    for (const el of data.elements || []) {
      points[el.id] = el?.stats?.total_points ?? 0;
    }
    return NextResponse.json({ event: Number(event), points });
  } catch {
    return NextResponse.json({ event: Number(event), points: {} });
  }
}
