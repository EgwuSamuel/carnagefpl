"use client";
import { useUser } from "@/lib/UserContext";
import { fmt1 } from "@/lib/format";
import { Loading, SectionTitle, Stat } from "@/components/ui";

export default function TransfersPage() {
  const { user, loadingModel, loadingUser } = useUser();
  if (loadingModel || loadingUser) return <Loading />;
  const t = user?.transfers;
  if (!t?.available)
    return <div className="text-white/50 py-16 text-center">{t?.note || "Set your team ID (top-right) to see transfer suggestions."}</div>;

  return (
    <div className="space-y-6">
      <SectionTitle hint={`horizon ${t.horizon} GWs`}>Transfer Planner</SectionTitle>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        <Stat label="In the bank" value={`£${fmt1(t.bank)}m`} accent="#00ff87" />
        <Stat label="Free transfers" value={t.free_transfers} accent="#04f5ff" />
        <Stat label="Best move gain" value={`+${fmt1(t.single_transfers?.[0]?.gain)}`} accent="#e90052"
          sub="pts / 5 GW" />
      </div>

      {/* single transfers */}
      <div className="card overflow-hidden">
        <div className="p-4 pb-2 font-bold">Best single transfers (this week)</div>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-white/45 text-xs uppercase">
              <th className="text-left p-3">Out</th>
              <th className="text-left p-3">In</th>
              <th className="text-right p-3">£ in</th>
              <th className="text-right p-3">Own%</th>
              <th className="text-right p-3">Gain 5GW</th>
              <th className="text-right p-3">After −4 hit</th>
            </tr>
          </thead>
          <tbody>
            {t.single_transfers?.map((s: any, i: number) => (
              <tr key={i} className="border-t border-white/5">
                <td className="p-3 text-white/70">{s.out} <span className="text-white/35 text-xs">{s.out_team}</span></td>
                <td className="p-3 font-semibold">{s.in} <span className="text-white/35 text-xs">{s.in_team}</span></td>
                <td className="p-3 text-right mono">{fmt1(s.in_price)}</td>
                <td className="p-3 text-right mono text-white/50">{fmt1(s.in_own)}</td>
                <td className="p-3 text-right mono font-bold text-fpl-green">+{fmt1(s.gain)}</td>
                <td className="p-3 text-right mono" style={{ color: s.gain_after_hit > 0 ? "#00ff87" : "#e90052" }}>
                  {s.gain_after_hit > 0 ? "+" : ""}{fmt1(s.gain_after_hit)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* 5-gw plan */}
      <div className="card overflow-hidden">
        <div className="p-4 pb-2 font-bold">Suggested 5-GW path <span className="text-white/40 text-xs font-normal">(1 free transfer / week)</span></div>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-white/45 text-xs uppercase">
              <th className="text-left p-3">GW</th>
              <th className="text-left p-3">Out</th>
              <th className="text-left p-3">In</th>
              <th className="text-right p-3">Gain</th>
              <th className="text-right p-3">Bank after</th>
            </tr>
          </thead>
          <tbody>
            {t.plan_5gw?.map((p: any, i: number) => (
              <tr key={i} className="border-t border-white/5">
                <td className="p-3 font-bold text-fpl-cyan">GW{p.gw}</td>
                <td className="p-3 text-white/70">{p.out}</td>
                <td className="p-3 font-semibold">{p.in}</td>
                <td className="p-3 text-right mono text-fpl-green">{p.gain > 0 ? "+" + fmt1(p.gain) : "—"}</td>
                <td className="p-3 text-right mono text-white/60">£{fmt1(p.bank_after)}m</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-white/40">{t.note}</p>
    </div>
  );
}
