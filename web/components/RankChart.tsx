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
  rankNow,
  nextEvent,
  horizon,
}: {
  projection: any[];
  rankNow: number;
  nextEvent: number;
  horizon?: number;
}) {
  const rows = (horizon ? projection.slice(0, horizon) : projection).map((p) => ({
    gw: p.event,
    p50: p.rank_p50,
    band: [p.rank_p10, p.rank_p90],
    low: p.rank_p10,
    high: p.rank_p90,
  }));
  // prepend "now"
  rows.unshift({ gw: nextEvent - 1, p50: rankNow, band: [rankNow, rankNow], low: rankNow, high: rankNow } as any);

  return (
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
              if (name === "p50") return [fmtRank(val), "projected (p50)"];
              return [fmtRank(val), name];
            }}
          />
          <Area type="monotone" dataKey="band" stroke="none" fill="url(#band)" />
          <Line
            type="monotone"
            dataKey="p50"
            stroke="#e90052"
            strokeWidth={2.5}
            dot={{ r: 2, fill: "#e90052" }}
            activeDot={{ r: 4 }}
          />
          <ReferenceLine y={rankNow} stroke="rgba(0,255,135,0.35)" strokeDasharray="4 4" />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
