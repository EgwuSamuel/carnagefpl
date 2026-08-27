"use client";
import { useMemo, useState } from "react";
import { useUser } from "@/lib/UserContext";
import { fmt1 } from "@/lib/format";
import { Loading, PosTag, SectionTitle } from "@/components/ui";

const COLS: [string, string][] = [
  ["xP_next", "xP next"],
  ["xP_H", "xP 5GW"],
  ["xP_attack", "Attack"],
  ["xP_cs", "Clean sheet"],
  ["xP_defcon", "DEFCON"],
  ["value_H", "Value"],
  ["own%", "Own%"],
  ["price", "£"],
];

export default function PlayersPage() {
  const { model } = useUser();
  const data = model ? { players: model.players } : null;
  const [pos, setPos] = useState("ALL");
  const [q, setQ] = useState("");
  const [sort, setSort] = useState("xP_H");

  const rows = useMemo(() => {
    if (!data?.players) return [];
    let r = data.players.filter((p: any) => p["p_start%"] >= 25);
    if (pos !== "ALL") r = r.filter((p: any) => p.pos === pos);
    if (q) r = r.filter((p: any) => (p.name + p.team).toLowerCase().includes(q.toLowerCase()));
    return r.sort((a: any, b: any) => (b[sort] ?? 0) - (a[sort] ?? 0)).slice(0, 120);
  }, [data, pos, q, sort]);

  if (!data) return <Loading />;

  return (
    <div className="space-y-4">
      <SectionTitle hint="top 120 by selected sort">Player database</SectionTitle>
      <div className="flex flex-wrap gap-2 items-center">
        {["ALL", "GKP", "DEF", "MID", "FWD"].map((p) => (
          <button
            key={p}
            onClick={() => setPos(p)}
            className={`px-3 py-1 rounded-lg text-sm font-semibold ${
              pos === p ? "bg-fpl-pink text-white" : "bg-white/5 text-white/60"
            }`}
          >
            {p}
          </button>
        ))}
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search player / team…"
          className="ml-auto bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-sm outline-none focus:border-fpl-pink"
        />
      </div>

      <div className="card overflow-x-auto">
        <table className="w-full text-sm min-w-[720px]">
          <thead>
            <tr className="text-white/45 text-xs uppercase">
              <th className="text-left p-3">Player</th>
              <th className="text-left p-3">Pos</th>
              {COLS.map(([k, label]) => (
                <th
                  key={k}
                  onClick={() => setSort(k)}
                  className={`text-right p-3 cursor-pointer select-none hover:text-white ${
                    sort === k ? "text-fpl-cyan" : ""
                  }`}
                >
                  {label} {sort === k ? "▾" : ""}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((p: any) => (
              <tr key={p.id} className="border-t border-white/5 hover:bg-white/5">
                <td className="p-3 font-semibold whitespace-nowrap">
                  {p.name} <span className="text-white/35 text-xs">{p.team}</span>
                  {p.pen === 1 && <span className="ml-1 pill bg-fpl-green/15 text-fpl-green">PK</span>}
                </td>
                <td className="p-3"><PosTag pos={p.pos} /></td>
                <td className="p-3 text-right mono">{fmt1(p.xP_next)}</td>
                <td className="p-3 text-right mono font-bold text-fpl-pink">{fmt1(p.xP_H)}</td>
                <td className="p-3 text-right mono text-white/70">{fmt1(p.xP_attack)}</td>
                <td className="p-3 text-right mono text-white/70">{fmt1(p.xP_cs)}</td>
                <td className="p-3 text-right mono text-white/70">{fmt1(p.xP_defcon)}</td>
                <td className="p-3 text-right mono text-fpl-cyan">{fmt1(p.value_H)}</td>
                <td className="p-3 text-right mono text-white/50">{fmt1(p["own%"])}</td>
                <td className="p-3 text-right mono">{fmt1(p.price)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
