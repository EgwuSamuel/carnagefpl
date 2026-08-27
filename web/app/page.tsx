"use client";
import { useState } from "react";
import { useUser } from "@/lib/UserContext";
import { fmtRank, fmtInt, fmt1, chipName } from "@/lib/format";
import { Stat, SectionTitle, Loading } from "@/components/ui";
import RankChart from "@/components/RankChart";

export default function Overview() {
  const { model, user, loadingModel, loadingUser, error } = useUser();
  const [horizon, setHorizon] = useState<5 | 38>(5);
  if (loadingModel) return <Loading />;

  const meta = model?.meta;
  const r = user?.rank;
  const e = r?.entry;
  const s = r?.summary;
  const proj = r?.projection || [];
  const topTransfer = user?.transfers?.single_transfers?.[0];

  return (
    <div className="space-y-6">
      {/* hero */}
      <div className="card p-5 sm:p-6 shadow-glow">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="text-white/50 text-sm">Manager</div>
            <div className="text-2xl font-black">
              {loadingUser ? "Loading…" : e?.name || "Set your team ID ↗"}
            </div>
            <div className="text-white/50 text-sm">{e?.player}</div>
          </div>
          {e && (
            <div className="text-right">
              <div className="text-white/50 text-xs uppercase tracking-wider">Overall rank</div>
              <div className="text-3xl font-black text-fpl-green mono">{fmtInt(e?.overall_rank)}</div>
              <div className="text-white/40 text-xs">
                of {fmtInt(e?.total_players)} · top {((e?.overall_rank / e?.total_players) * 100).toFixed(1)}%
              </div>
            </div>
          )}
        </div>
        {error && (
          <div className="mt-3 text-sm text-fpl-pink">
            {error} — use the team button (top-right) to enter a valid FPL ID.
          </div>
        )}
      </div>

      {e && (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <Stat label="Total points" value={fmtInt(e?.overall_points)} accent="#04f5ff" sub={`after GW${e?.current_event}`} />
            <Stat label="Team value" value={`£${fmt1(e?.team_value)}m`} accent="#00ff87" sub={`£${fmt1(e?.bank)}m in bank`} />
            <Stat label={`Proj. rank · GW${meta?.next_event + 4}`} value={fmtRank(s?.rank_gw5_p50)} accent="#e90052" sub={`${fmtRank(s?.rank_gw5_p10)} – ${fmtRank(s?.rank_gw5_p90)}`} />
            <Stat label="Proj. rank · GW38" value={fmtRank(s?.rank_gw38_p50)} accent="#ffb703" sub={`${fmtRank(s?.rank_gw38_p10)} – ${fmtRank(s?.rank_gw38_p90)}`} />
          </div>

          <div className="card p-5">
            <SectionTitle hint={`updated ${meta?.updated}`}>Rank projection</SectionTitle>
            <div className="flex gap-2 mb-3">
              {[5, 38].map((h) => (
                <button key={h} onClick={() => setHorizon(h as 5 | 38)}
                  className={`px-3 py-1 rounded-lg text-sm font-semibold ${horizon === h ? "bg-fpl-pink text-white" : "bg-white/5 text-white/60"}`}>
                  Next {h} GWs
                </button>
              ))}
            </div>
            <RankChart projection={proj} planLine={user?.rankWithPlan?.projection} rankNow={e?.overall_rank} nextEvent={meta?.next_event} horizon={horizon === 5 ? 5 : undefined} />
            <p className="text-xs text-white/40 mt-3 leading-relaxed">
              <span className="text-fpl-pink">Pink</span> = rank if you hold this squad (shaded band =
              10th–90th percentile, Monte-Carlo). <span className="text-fpl-green">Green dashed</span> =
              rank if you apply the recommended 5-GW transfers — the gap between them is the edge those
              moves buy you. See the <span className="text-fpl-cyan">Transfers</span> tab for the moves.
            </p>
          </div>

          <div className="grid md:grid-cols-2 gap-4">
            <div className="card p-5">
              <SectionTitle hint="highest 5-GW gain">Top transfer move</SectionTitle>
              {topTransfer ? (
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-white/50 text-xs">OUT</div>
                    <div className="font-bold text-white/80">{topTransfer.out} <span className="text-white/40 text-xs">{topTransfer.out_team}</span></div>
                  </div>
                  <div className="text-2xl text-fpl-pink">→</div>
                  <div className="text-right">
                    <div className="text-white/50 text-xs">IN</div>
                    <div className="font-bold">{topTransfer.in} <span className="text-white/40 text-xs">{topTransfer.in_team} £{topTransfer.in_price}m</span></div>
                  </div>
                  <div className="ml-4 text-right">
                    <div className="text-fpl-green font-black text-xl mono">+{fmt1(topTransfer.gain)}</div>
                    <div className="text-white/40 text-xs">pts / 5 GW</div>
                  </div>
                </div>
              ) : (<div className="text-white/40 text-sm">No clear upgrade available.</div>)}
            </div>

            <div className="card p-5">
              <SectionTitle>Chips used</SectionTitle>
              {r?.chips_used?.length ? (
                <div className="flex flex-wrap gap-2">
                  {r.chips_used.map((c: any, i: number) => (
                    <span key={i} className="pill bg-fpl-purple/60 text-fpl-cyan border border-fpl-cyan/30">{chipName(c.name)} · GW{c.event}</span>
                  ))}
                </div>
              ) : (<div className="text-white/40 text-sm">None used yet.</div>)}
              <div className="mt-4 space-y-1">
                {model?.chips_notes?.slice(0, 4).map((n: string, i: number) => (
                  <div key={i} className="text-xs text-white/45">• {n}</div>
                ))}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
