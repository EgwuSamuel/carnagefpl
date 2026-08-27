"use client";
import { useEffect, useState } from "react";

// Live in-match points via our serverless proxy (falls back silently).
export function useLive(event: number | undefined) {
  const [live, setLive] = useState<any>(null);
  useEffect(() => {
    if (!event) return;
    fetch(`/api/live?event=${event}`, { cache: "no-store" })
      .then((r) => r.json())
      .then(setLive)
      .catch(() => setLive(null));
  }, [event]);
  return live;
}
