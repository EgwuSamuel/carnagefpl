"use client";
import { useState } from "react";
import { useUser } from "@/lib/UserContext";

export default function EntryPicker() {
  const { entryId, setEntryId, user, loadingUser, error } = useUser();
  const [open, setOpen] = useState(false);
  const [val, setVal] = useState(entryId);

  const name = user?.entry?.name;
  const label = loadingUser ? "Loading…" : name || "Set your team";

  const save = () => {
    const clean = val.replace(/[^\d]/g, "");
    if (clean) { setEntryId(clean); setOpen(false); }
  };

  return (
    <div className="relative ml-auto">
      <button
        onClick={() => { setVal(entryId); setOpen((o) => !o); }}
        className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-semibold bg-white/5 hover:bg-white/10 border border-white/10"
      >
        <span className="h-2 w-2 rounded-full bg-fpl-green" />
        <span className="max-w-[130px] truncate">{label}</span>
        <span className="text-white/40">▾</span>
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute right-0 mt-2 w-80 card p-4 z-50 shadow-glow">
            <div className="font-bold mb-1">Your FPL Team ID</div>
            <p className="text-xs text-white/55 leading-relaxed mb-3">
              On the FPL site open <span className="text-fpl-cyan">Points</span> or{" "}
              <span className="text-fpl-cyan">Gameweek&nbsp;History</span>. Your ID is the number in
              the URL:
              <br />
              <span className="mono text-white/70">
                …/entry/<span className="text-fpl-pink font-bold">8611170</span>/…
              </span>
            </p>
            <div className="flex gap-2">
              <input
                value={val}
                onChange={(e) => setVal(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && save()}
                inputMode="numeric"
                placeholder="e.g. 8611170"
                className="flex-1 bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-sm outline-none focus:border-fpl-pink mono"
              />
              <button
                onClick={save}
                className="px-3 py-1.5 rounded-lg text-sm font-bold bg-fpl-pink text-white"
              >
                Go
              </button>
            </div>
            {error && <div className="text-xs text-fpl-pink mt-2">{error}</div>}
            {user?.entry && !error && (
              <div className="text-xs text-white/50 mt-2">
                Showing: <span className="text-white/80">{user.entry.name}</span> ·{" "}
                {user.entry.player_first_name} {user.entry.player_last_name}
              </div>
            )}
            <div className="text-[11px] text-white/35 mt-3">
              Saved on this device only. Public data — no login needed.
            </div>
          </div>
        </>
      )}
    </div>
  );
}
