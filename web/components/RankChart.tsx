"use client";
import {
  Area,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  CartesianGrid,
  ReferenceLine,
} from "recharts";
import { fmtRank } from "@/lib/format";

export default function RankChart({
  projection,
  planLine,
  rankNow,
  nextEvent,
  horizon,
}: {
  projection: any[];
  planLine?: any[];
  rankNow: number;
  nextEvent: number;
  horizon?: number;
}) {
  const planByEvent: Record<number, number> = {};
  (planLine || []).forEach((p) => (planByEvent[p.event] = p.rank_p50));
  const rows = (horizon ? projection.slice(0, horizon) : projection).map((p) => ({
    gw: p.event,
    p50: p.rank_p50,
    plan: planByEvent[p.event],
    band: [p.rank_p10, p.rank_p90],
  }));
  // prepend "now"
  rows.unshift({ gw: nextEvent - 1, p50: rankNow, plan: rankNow, band: [rankNow, rankNow] } as any);

  return (
    <div className="w-full">
      <div className="h-72 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={rows} margin={{ top: 10, right: 12, left: 4, bottom: 0 }}>
          <defs>
            <linearGradient id="band" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#04f5ff" stopOpacity={0.25} />
              <stop offset="100%" stopColor="#04f5ff" stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
          <XAxis
            dataKey="gw"
            tick={{ fill: "rgba(255,255,255,0.5)", fontSize: 11 }}
            tickFormatter={(v) => `GW${v}`}
          />
          <YAxis
            reversed
            tick={{ fill: "rgba(255,255,255,0.5)", fontSize: 11 }}
            tickFormatter={(v) => fmtRank(v)}
            width={48}
            domain={["dataMin", "dataMax"]}
          />
          <Tooltip
            contentStyle={{
              background: "#12101c",
              border: "1px solid rgba(255,255,255,0.12)",
              borderRadius: 12,
              fontSize: 12,
            }}
            labelFormatter={(v) => `Gameweek ${v}`}
            formatter={(val: any, name: any) => {
              if (name === "band") return [`${fmtRank(val[0])} – ${fmtRank(val[1])}`, "range (p10–p90)"];
              if (name === "p50") return [fmtRank(val), "hold squad"];
              if (name === "plan") return [fmtRank(val), "with transfers"];
              return [fmtRank(val), name];
            }}
          />
          <Area type="monotone" dataKey="band" stroke="none" fill="url(#band)" />
          <Line type="monotone" dataKey="p50" stroke="#e90052" strokeWidth={2.5}
            dot={{ r: 2, fill: "#e90052" }} activeDot={{ r: 4 }} />
          {planLine && planLine.length > 0 && (
            <Line type="monotone" dataKey="plan" stroke="#00ff87" strokeWidth={2.5}
              strokeDasharray="5 3" dot={false} activeDot={{ r: 4 }} connectNulls />
          )}
          <ReferenceLine y={rankNow} stroke="rgba(255,255,255,0.18)" strokeDasharray="4 4" />
        </ComposedChart>
      </ResponsiveContainer>
      </div>
      <div className="flex gap-4 justify-center mt-2 text-xs">
        <span className="flex items-center gap-1.5"><span className="inline-block w-4 h-0.5 bg-fpl-pink" /> Hold squad</span>
        {planLine && planLine.length > 0 && (
          <span className="flex items-center gap-1.5"><span className="inline-block w-4 h-0.5" style={{ background: "#00ff87" }} /> With recommended transfers</span>
        )}
      </div>
    </div>
  );
}
