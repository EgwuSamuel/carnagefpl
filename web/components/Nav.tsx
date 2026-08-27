"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import EntryPicker from "@/components/EntryPicker";

const TABS = [
  { href: "/", label: "Overview" },
  { href: "/squad", label: "My Squad" },
  { href: "/transfers", label: "Transfers" },
  { href: "/players", label: "Players" },
  { href: "/insights", label: "Insights" },
  { href: "/fixtures", label: "Fixtures" },
];

export default function Nav() {
  const path = usePathname();
  return (
    <header className="sticky top-0 z-30 backdrop-blur-md bg-ink-900/70 border-b border-white/10">
      <div className="max-w-6xl mx-auto px-4 flex items-center gap-1 h-14">
        <Link href="/" className="flex items-center gap-2.5 mr-4 shrink-0">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="/logo.jpg"
            alt="Carnage FPL"
            className="h-9 w-9 rounded-full object-cover ring-1 ring-white/15 shadow-glow"
          />
          <span className="text-xl font-black tracking-tight hidden sm:inline">
            <span className="text-fpl-pink">CARNAGE</span>
            <span className="text-fpl-cyan">FPL</span>
          </span>
        </Link>
        <nav className="flex items-center gap-1 overflow-x-auto">
          {TABS.map((t) => {
            const active = t.href === "/" ? path === "/" : path.startsWith(t.href);
            return (
              <Link
                key={t.href}
                href={t.href}
                className={`px-3 py-1.5 rounded-lg text-sm font-semibold whitespace-nowrap transition ${
                  active
                    ? "bg-fpl-pink text-white shadow-glow"
                    : "text-white/60 hover:text-white hover:bg-white/5"
                }`}
              >
                {t.label}
              </Link>
            );
          })}
        </nav>
        <EntryPicker />
      </div>
    </header>
  );
}
