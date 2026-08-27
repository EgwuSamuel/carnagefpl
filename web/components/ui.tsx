"use client";
import { posColor } from "@/lib/format";

export function Stat({
  label,
  value,
  sub,
  accent = "#e90052",
}: {
  label: string;
  value: React.ReactNode;
  sub?: React.ReactNode;
  accent?: string;
}) {
  return (
    <div className="card card-hover p-4 flex flex-col gap-1">
      <div className="text-[11px] uppercase tracking-wider text-white/45">{label}</div>
      <div className="text-2xl font-black mono" style={{ color: accent }}>
        {value}
      </div>
      {sub != null && <div className="text-xs text-white/50">{sub}</div>}
    </div>
  );
}

export function PosTag({ pos }: { pos: string }) {
  return (
    <span
      className="pill"
      style={{ background: posColor(pos) + "22", color: posColor(pos) }}
    >
      {pos}
    </span>
  );
}

export function SectionTitle({
  children,
  hint,
}: {
  children: React.ReactNode;
  hint?: string;
}) {
  return (
    <div className="flex items-end justify-between mb-3">
      <h2 className="text-lg font-bold">{children}</h2>
      {hint && <span className="text-xs text-white/40">{hint}</span>}
    </div>
  );
}

export function Loading() {
  return (
    <div className="max-w-6xl mx-auto px-4 py-20 text-center text-white/50">
      <div className="inline-block h-8 w-8 rounded-full border-2 border-fpl-pink border-t-transparent animate-spin mb-3" />
      <div>Loading model…</div>
    </div>
  );
}
