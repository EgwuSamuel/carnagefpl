export const fmtRank = (n: number | null | undefined) => {
  if (n == null) return "—";
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(2) + "M";
  if (n >= 1_000) return (n / 1_000).toFixed(0) + "k";
  return String(n);
};

export const fmtInt = (n: number | null | undefined) =>
  n == null ? "—" : n.toLocaleString("en-GB");

export const fmt1 = (n: number | null | undefined) =>
  n == null ? "—" : (Math.round(n * 10) / 10).toFixed(1);

// FDR 1 (easy) .. 5 (hard) -> colour
export const fdrColor = (fdr: number) =>
  ({ 1: "#00ff87", 2: "#7be0a0", 3: "#e7e756", 4: "#ff8a5b", 5: "#e90052" } as any)[
    Math.round(fdr)
  ] || "#555";

export const fdrText = (fdr: number) => (Math.round(fdr) <= 2 ? "#04202a" : "#1a0010");

export const posColor = (pos: string) =>
  ({ GKP: "#04f5ff", DEF: "#00ff87", MID: "#e90052", FWD: "#ffb703" } as any)[pos] ||
  "#aaa";

export const chipName = (c: string) =>
  ({
    bboost: "Bench Boost",
    "3xc": "Triple Captain",
    freehit: "Free Hit",
    wildcard: "Wildcard",
  } as any)[c] || c;
