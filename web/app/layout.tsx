import type { Metadata } from "next";
import "./globals.css";
import Nav from "@/components/Nav";
import { UserProvider } from "@/lib/UserContext";
import AppGate from "@/components/AppGate";

export const metadata: Metadata = {
  title: "Carnage FPL",
  description: "Expected-points model, rank projection & transfer planner for Fantasy Premier League",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <UserProvider>
          <Nav />
          <main className="max-w-6xl mx-auto px-4 py-6">
            <AppGate>{children}</AppGate>
          </main>
        </UserProvider>
        <footer className="max-w-6xl mx-auto px-4 py-10 text-center text-xs text-white/30">
          Carnage FPL · model-based projections, not guarantees · data © Premier League / FPL
        </footer>
      </body>
    </html>
  );
}
