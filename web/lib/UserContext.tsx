"use client";
import { createContext, useContext, useEffect, useState, useCallback } from "react";
import { projectRank, planTransfers, buildSquad } from "@/lib/model";

type Ctx = {
  model: any;
  entryId: string;
  setEntryId: (id: string) => void;
  loadingModel: boolean;
  loadingUser: boolean;
  error: string | null;
  user: any;
};

const UserCtx = createContext<Ctx>({} as any);
export const useUser = () => useContext(UserCtx);

const KEY = "carnage_fpl_entry";

export function UserProvider({ children }: { children: React.ReactNode }) {
  const [model, setModel] = useState<any>(null);
  const [entryId, setEntryIdState] = useState<string>("");
  const [user, setUser] = useState<any>(null);
  const [loadingUser, setLoadingUser] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // load model.json + resolve initial entry id
  useEffect(() => {
    fetch("/data/model.json", { cache: "no-store" })
      .then((r) => r.json())
      .then((m) => {
        setModel(m);
        let saved = "";
        try { saved = localStorage.getItem(KEY) || ""; } catch {}
        setEntryIdState(saved || String(m.config?.default_entry || ""));
      })
      .catch(() => setError("Failed to load model data."));
  }, []);

  const setEntryId = useCallback((id: string) => {
    const clean = id.replace(/[^\d]/g, "");
    setEntryIdState(clean);
    try { localStorage.setItem(KEY, clean); } catch {}
  }, []);

  // recompute whenever model or entryId changes
  useEffect(() => {
    if (!model || !entryId) return;
    let cancelled = false;
    setLoadingUser(true);
    setError(null);
    fetch(`/api/manager?id=${entryId}`, { cache: "no-store" })
      .then(async (r) => {
        const d = await r.json();
        if (!r.ok) throw new Error(d.error || "Lookup failed.");
        return d;
      })
      .then((d) => {
        if (cancelled) return;
        const { squad, captainId } = buildSquad(model, d.picks);
        const pickIds = squad.map((p: any) => p.id);
        const rank = projectRank(model, d.entry, d.history, pickIds, captainId);
        const transfers = planTransfers(model, pickIds, rank._bank || 0);
        // second line: rank if you APPLY the recommended 5-GW transfer path
        const plan = (transfers?.plan_5gw || [])
          .filter((r: any) => r.out_id)
          .map((r: any) => ({ gw: r.gw, out_id: r.out_id, in_id: r.in_id }));
        const rankWithPlan = plan.length
          ? projectRank(model, d.entry, d.history, pickIds, captainId, { transfers: plan, mc: false })
          : null;
        setUser({ entry: d.entry, history: d.history, squad, captainId, rank, rankWithPlan, transfers });
      })
      .catch((e) => { if (!cancelled) { setError(String(e.message || e)); setUser(null); } })
      .finally(() => { if (!cancelled) setLoadingUser(false); });
    return () => { cancelled = true; };
  }, [model, entryId]);

  return (
    <UserCtx.Provider
      value={{ model, entryId, setEntryId, loadingModel: !model, loadingUser, error, user }}
    >
      {children}
    </UserCtx.Provider>
  );
}
