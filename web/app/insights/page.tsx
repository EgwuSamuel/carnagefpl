"use client";
import { useState } from "react";
import { useUser } from "@/lib/UserContext";
import { Loading, PosTag, SectionTitle, Stat } from "@/components/ui";
import { fmt1 } from "@/lib/format";

const SUBTABS = ["Rankings", "Watchlist", "Set Pieces", "Dream Team"] as const;

function cell(v: any) {
  if (v == null || v === "") return "—";
  if (typeof v === "number") return Number.isInteger(v) ? v : fmt1(v);
  return String(v);
}

function Table({ rows, highlight }: { rows: any[]; highlight?: string }) {
  if (!rows?.length) return <div className="text-white/40 text-sm p-3">No data.</div>;
  const cols = Object.keys(rows[0]);
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-white/45 text-xs uppercase">
            {cols.map((c) => (
              <th key={c} className={`p-2 ${typeof rows[0][c] === "number" ? "text-right" : "text-left"}`}>{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} className="border-t border-white/5 hover:bg-white/5">
              {cols.map((c) => (
                <td
                  key={c}
                  className={`p-2 ${typeof r[c] === "number" ? "text-right mono" : ""} ${
                    c === "pos" ? "" : ""
                  } ${highlight && c === highlight ? "font-bold text-fpl-pink" : ""}`}
                >
                  {c === "pos" ? <PosTag pos={r[c]} /> : c === "name" ? <span className="font-semibold">{r[c]}</span> : cell(r[c])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function InsightsPage() {
  const { model, loadingModel } = useUser();
  const [tab, setTab] = useState<(typeof SUBTABS)[number]>("Rankings");
  const [team, setTeam] = useState("ALL");
  if (loadingModel) return <Loading />;

  const rankings = model.rankings || {};
  const watchlist = model.watchlist || [];
  const setpieces = model.setpieces || [];
  const opt = model.optimiser;
  const teams = ["ALL", ...Array.from(new Set(watchlist.map((w: any) => w.team))).sort()];

  return (
    <div className="space-y-5">
      <SectionTitle hint="model-derived shortlists">Insights</SectionTitle>
      <div className="flex flex-wrap gap-2">
        {SUBTABS.map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-3 py-1.5 rounded-lg text-sm font-semibold ${tab === t ? "bg-fpl-pink text-white" : "bg-white/5 text-white/60"}`}>
            {t}
          </button>
        ))}
      </div>

      {tab === "Rankings" && (
        <div className="grid md:grid-cols-2 gap-4">
          {Object.entries(rankings).map(([title, rows]: any) => (
            <div key={title} className="card p-4">
              <div className="font-bold mb-2 text-sm">{title}</div>
              <Table rows={rows} highlight="xP_H" />
            </div>
          ))}
        </div>
      )}

      {tab === "Watchlist" && (
        <div className="card p-4">
          <div className="flex items-center justify-between mb-2">
            <div className="font-bold text-sm">Best 2–3 targets in every club</div>
            <select value={team} onChange={(e) => setTeam(e.target.value)}
              className="bg-white/5 border border-white/10 rounded-lg px-2 py-1 text-sm outline-none">
              {teams.map((t: string) => <option key={t} value={t} className="bg-ink-800">{t}</option>)}
            </select>
          </div>
          <Table rows={team === "ALL" ? watchlist : watchlist.filter((w: any) => w.team === team)} highlight="xP_H" />
        </div>
      )}

      {tab === "Set Pieces" && (
        <div className="card p-4">
          <div className="font-bold mb-2 text-sm">Penalty / free-kick / corner takers (order 1 = first choice)</div>
          <Table rows={setpieces} />
        </div>
      )}

      {tab === "Dream Team" && opt && (
        <div className="space-y-4">
          <div className="grid grid-cols-3 gap-3">
            <Stat label="Squad cost" value={`£${fmt1(opt.cost)}m`} accent="#00ff87" />
            <Stat label="XI xP (5 GW)" value={fmt1(opt.xi_xp)} accent="#e90052" />
            <Stat label="Captain" value={opt.captain} accent="#04f5ff" />
          </div>
          <div className="card p-4">
            <div className="font-bold mb-2 text-sm">Optimised best legal 15 (£100m, max 3/club)</div>
            <Table rows={opt.players} highlight="xP_H" />
          </div>
        </div>
      )}
    </div>
  );
}
