"use client";
import { useState } from "react";
import { useUser } from "@/lib/UserContext";

export default function Onboarding() {
  const { setEntryId, error, model } = useUser();
  const [val, setVal] = useState("");
  const [touched, setTouched] = useState(false);

  const go = () => {
    const clean = val.replace(/[^\d]/g, "");
    setTouched(true);
    if (clean) setEntryId(clean);
  };
  const sample = model?.config?.default_entry;

  return (
    <div className="min-h-[calc(100vh-8rem)] flex items-center justify-center px-4 py-10">
      <div className="w-full max-w-lg text-center">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src="/logo.jpg"
          alt="Carnage FPL"
          className="h-24 w-24 rounded-full object-cover ring-2 ring-fpl-pink/40 shadow-glow mx-auto mb-5"
        />
        <h1 className="text-3xl font-black tracking-tight">
          <span className="text-fpl-pink">CARNAGE</span>{" "}
          <span className="text-fpl-cyan">FPL</span>
        </h1>
        <p className="text-white/55 mt-2 mb-7 text-sm">
          Expected-points model, rank projection & transfer planner for Fantasy Premier League.
        </p>

        <div className="card p-6 text-left shadow-glow">
          <label className="block font-bold mb-1">Enter your FPL Team ID to begin</label>
          <p className="text-xs text-white/50 mb-3">It’s public — no login or password needed.</p>
          <div className="flex gap-2">
            <input
              autoFocus
              value={val}
              onChange={(e) => setVal(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && go()}
              inputMode="numeric"
              placeholder="e.g. 8611170"
              className="flex-1 bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 outline-none focus:border-fpl-pink mono text-lg"
            />
            <button
              onClick={go}
              className="px-5 py-2.5 rounded-lg font-bold bg-fpl-pink text-white shadow-glow hover:brightness-110"
            >
              Go →
            </button>
          </div>
          {touched && !val.replace(/[^\d]/g, "") && (
            <div className="text-xs text-fpl-pink mt-2">Enter the numeric ID from your team URL.</div>
          )}
          {error && <div className="text-xs text-fpl-pink mt-2">{error}</div>}

          {/* hint */}
          <div className="mt-5 rounded-xl bg-fpl-purple/30 border border-white/10 p-4">
            <div className="text-xs font-bold text-fpl-cyan uppercase tracking-wider mb-2">
              How to find your ID
            </div>
            <ol className="text-sm text-white/70 space-y-1.5 list-decimal list-inside">
              <li>
                Sign in at{" "}
                <span className="text-white">fantasy.premierleague.com</span>.
              </li>
              <li>
                Open the <span className="text-white font-semibold">Points</span> tab (or{" "}
                <span className="text-white font-semibold">Gameweek History</span>).
              </li>
              <li>Your ID is the number in the address bar:</li>
            </ol>
            <div className="mt-2 mono text-sm bg-black/40 rounded-lg px-3 py-2 overflow-x-auto whitespace-nowrap">
              …/entry/<span className="text-fpl-pink font-bold">8611170</span>/event/1
            </div>
            <div className="text-[11px] text-white/40 mt-2">
              Here the ID is <span className="text-fpl-pink font-bold">8611170</span>. Yours is saved on this device only.
            </div>
          </div>

          {sample && (
            <button
              onClick={() => setEntryId(String(sample))}
              className="mt-4 text-sm text-white/50 hover:text-fpl-cyan transition"
            >
              Just exploring? View a sample team →
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
