import type { Metadata } from "next";
import Link from "next/link";
import { JetBrains_Mono, Public_Sans } from "next/font/google";
import type { ReactNode } from "react";
import { loadIndex } from "@/lib/data";
import "./globals.css";

// JetBrains Mono was designed specifically to disambiguate similar-looking
// characters (0/O, 1/l/I, and a clear @) — the exact property this page
// needs when it's rendering character-level diffs of near-identical
// package names.
const mono = JetBrains_Mono({
  subsets: ["latin"],
  weight: ["400", "700"],
  variable: "--font-mono",
  display: "swap",
});

const publicSans = Public_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-sans",
  display: "swap",
});

export const metadata: Metadata = {
  title: "mcphound — MCP server reputation",
  description: "Independent security scores for public Model Context Protocol servers.",
};

function NavLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <Link
      href={href}
      className="font-mono text-[11px] uppercase tracking-widest2 text-paper-dim transition-colors hover:text-signal"
    >
      {children}
    </Link>
  );
}

export default function RootLayout({ children }: { children: ReactNode }) {
  let watchCount: number | null = null;
  try {
    watchCount = loadIndex().length;
  } catch {
    watchCount = null;
  }

  return (
    <html lang="en" className={`${mono.variable} ${publicSans.variable}`}>
      <body className="min-h-screen bg-ink-950 font-sans text-paper antialiased">
        <a
          href="#main"
          className="absolute left-2 top-2 -translate-y-16 bg-signal px-3 py-1.5 font-mono text-xs text-ink-950 transition-transform focus:translate-y-0"
        >
          Skip to content
        </a>
        <header className="border-b border-ink-700 bg-ink-900/60">
          <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-x-8 gap-y-3 px-6 py-4">
            <div className="flex items-baseline gap-3">
              <Link href="/" className="font-mono text-lg font-bold tracking-tight text-paper">
                mcphound
              </Link>
              <span className="hidden font-mono text-[11px] text-paper-dim sm:inline">
                night watch over the MCP registry
              </span>
            </div>
            <nav className="flex items-center gap-6">
              <NavLink href="/">Flagged</NavLink>
              <NavLink href="/browse/1">Registry</NavLink>
              <NavLink href="/typosquats">Typosquats</NavLink>
            </nav>
          </div>
          {watchCount !== null && (
            <div className="border-t border-ink-800 bg-ink-950/60">
              <div className="mx-auto flex max-w-5xl items-center gap-2 px-6 py-1.5 font-mono text-[11px] text-paper-dim">
                <span className="h-1.5 w-1.5 rounded-full bg-clear" aria-hidden />
                <span>
                  {watchCount} server{watchCount === 1 ? "" : "s"} on watch
                </span>
              </div>
            </div>
          )}
        </header>
        <main id="main" className="mx-auto max-w-5xl px-6 py-10">
          {children}
        </main>
        <footer className="mt-16 border-t border-ink-700">
          <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-4 px-6 py-6 font-mono text-[11px] text-paper-dim">
            <p>Static analysis only — mcphound never executes a server to score it.</p>
            <div className="flex gap-5">
              <a
                href="https://github.com/markdoyle4312-hash/mcphound"
                className="transition-colors hover:text-signal"
              >
                Source
              </a>
              <a
                href="https://pypi.org/project/mcphound/"
                className="transition-colors hover:text-signal"
              >
                PyPI
              </a>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
