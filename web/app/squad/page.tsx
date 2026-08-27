"use client";
import { useLive } from "@/lib/useData";
import { useUser } from "@/lib/UserContext";
import { fmt1, posColor } from "@/lib/format";
import { Loading, PosTag, SectionTitle, Stat } from "@/components/ui";

export default function SquadPage() {
  const { model, user, loadingModel } = useUser();
  const liveRaw = useLive(model?.meta?.next_event);
  const live =
    liveRaw && Object.values(liveRaw.points || {}).some((v: any) => v > 0)
      ? liveRaw
      : null;
  if (loadingModel) return <Loading />;
  const squad = user?.squad || [];
  const totalNext = squad.reduce(
    (a: number, p: any) => a + (p.xP_next || 0) * (p.is_captain ? 2 : 1),
    0
  );
  const weak = [...squad]
    .filter((p: any) => p.nailed >= 40)
    .sort((a: any, b: any) => a.xP_H - b.xP_H)
    .slice(0, 3)
    .map((p: any) => p.id);

  return (
    <div className="space-y-6">
      <SectionTitle hint="pulled live from your FPL team">My Squad</SectionTitle>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <Stat label="Proj. next GW" value={fmt1(totalNext)} accent="#e90052" sub="incl. captain" />
        <Stat label="Players flagged" value={squad.filter((p: any) => p.status !== "a").length}
          accent="#ffb703" sub="injury / doubt" />
        <Stat label="Weak links" value={weak.length} accent="#04f5ff" sub="lowest 5-GW xP" />
        <Stat label="Squad size" value={squad.length} accent="#00ff87" />
      </div>

      <div className="card overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-white/45 text-xs uppercase">
              <th className="text-left p-3">Player</th>
              <th className="text-left p-3">Pos</th>
              <th className="text-right p-3">£</th>
              <th className="text-right p-3">Own%</th>
              <th className="text-right p-3">Nailed</th>
              <th className="text-right p-3">xP next</th>
              <th className="text-right p-3">xP 5GW</th>
              {live && <th className="text-right p-3 text-fpl-green">Live</th>}
            </tr>
          </thead>
          <tbody>
            {squad.map((p: any) => (
              <tr
                key={p.id}
                className={`border-t border-white/5 ${
                  weak.includes(p.id) ? "bg-fpl-pink/5" : ""
                }`}
              >
                <td className="p-3 font-semibold">
                  {p.name}
                  {p.is_captain && (
                    <span className="ml-1 pill bg-fpl-pink text-white">C</span>
                  )}
                  <span className="ml-2 text-white/35 text-xs">{p.team}</span>
                  {p.status !== "a" && (
                    <span className="ml-2 pill bg-yellow-500/20 text-yellow-300">
                      {p.status.toUpperCase()}
                    </span>
                  )}
                </td>
                <td className="p-3"><PosTag pos={p.pos} /></td>
                <td className="p-3 text-right mono">{fmt1(p.price)}</td>
                <td className="p-3 text-right mono text-white/60">{fmt1(p.own)}</td>
                <td className="p-3 text-right mono">
                  <span style={{ color: p.nailed >= 70 ? "#00ff87" : p.nailed >= 40 ? "#ffb703" : "#e90052" }}>
                    {p.nailed}%
                  </span>
                </td>
                <td className="p-3 text-right mono">{fmt1(p.xP_next)}</td>
                <td className="p-3 text-right mono font-bold" style={{ color: posColor(p.pos) }}>
                  {fmt1(p.xP_H)}
                </td>
                {live && (
                  <td className="p-3 text-right mono font-bold text-fpl-green">
                    {live.points?.[p.id] ?? 0}
                    {p.is_captain ? " ×2" : ""}
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-white/40">
        Rows highlighted pink are your lowest-xP likely starters — prime transfer candidates.
        Live column appears during an in-progress gameweek.
      </p>
    </div>
  );
}
