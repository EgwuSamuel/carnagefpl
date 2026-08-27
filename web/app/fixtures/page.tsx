"use client";
import { useUser } from "@/lib/UserContext";
import { fdrColor, fdrText } from "@/lib/format";
import { Loading, SectionTitle } from "@/components/ui";

export default function FixturesPage() {
  const { model, loadingModel } = useUser();
  if (loadingModel) return <Loading />;
  const fx = model.fixtures;
  const events: number[] = fx?.events || [];
  const teams = Object.keys(fx?.rows || {}).sort();

  // sort teams by easiest average FDR over the window
  const avg = (t: string) => {
    const vals = events
      .map((e) => fx.rows[t][String(e)]?.fdr)
      .filter((v: any) => v != null);
    return vals.length ? vals.reduce((a: number, b: number) => a + b, 0) / vals.length : 9;
  };
  teams.sort((a, b) => avg(a) - avg(b));

  return (
    <div className="space-y-4">
      <SectionTitle hint="green = easy · red = hard · DBL = double GW">Fixture Tracker</SectionTitle>
      <div className="card overflow-x-auto p-3">
        <table className="border-separate border-spacing-1 min-w-[640px]">
          <thead>
            <tr>
              <th className="text-left text-xs text-white/45 px-2 sticky left-0 bg-ink-900">Team</th>
              {events.map((e) => (
                <th key={e} className="text-xs text-white/45 px-2">GW{e}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {teams.map((t) => (
              <tr key={t}>
                <td className="text-sm font-bold px-2 sticky left-0 bg-ink-900">{t}</td>
                {events.map((e) => {
                  const cell = fx.rows[t][String(e)];
                  if (!cell)
                    return (
                      <td key={e} className="text-center text-xs text-white/25 rounded-md"
                        style={{ background: "rgba(255,255,255,0.03)", minWidth: 62 }}>
                        —
                      </td>
                    );
                  return (
                    <td
                      key={e}
                      className="text-center text-[11px] font-semibold rounded-md px-1 py-1.5"
                      style={{ background: fdrColor(cell.fdr), color: fdrText(cell.fdr), minWidth: 62 }}
                      title={`FDR ${cell.fdr}`}
                    >
                      {cell.text}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-white/40">
        Teams sorted by easiest run first. Buy a team before a green run; sell before a red one.
      </p>
    </div>
  );
}
