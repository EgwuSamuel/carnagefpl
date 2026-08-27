"use client";
import { useUser } from "@/lib/UserContext";
import Onboarding from "@/components/Onboarding";
import { Loading } from "@/components/ui";

export default function AppGate({ children }: { children: React.ReactNode }) {
  const { resolved, model, entryId, error, user, loadingUser } = useUser();

  if (!resolved || (!model && !error)) return <Loading />;
  if (error && !model)
    return <div className="max-w-lg mx-auto py-24 text-center text-white/60">{error}</div>;

  // first visit (no saved id) OR an invalid id that returned no team → onboard
  if (!entryId) return <Onboarding />;
  if (error && !user && !loadingUser) return <Onboarding />;

  return <>{children}</>;
}
