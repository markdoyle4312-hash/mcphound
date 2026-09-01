import type { Metadata, Viewport } from "next";
import Link from "next/link";
import { JetBrains_Mono, Public_Sans } from "next/font/google";
import type { ReactNode } from "react";
import { loadIndex } from "@/lib/data";
import { jsonLdScript } from "@/lib/jsonld";
import { NavLink } from "@/components/NavLink";
import { SearchBox } from "@/components/SearchBox";
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

const SITE_URL = "https://mcphound.dev";
const SITE_DESCRIPTION =
  "Independent security scores for public Model Context Protocol servers.";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: "mcphound — MCP server reputation",
    template: "%s · mcphound",
  },
  description: SITE_DESCRIPTION,
  openGraph: {
    type: "website",
    siteName: "mcphound",
    title: "mcphound — MCP server reputation",
    description: SITE_DESCRIPTION,
  },
  twitter: {
    card: "summary_large_image",
    title: "mcphound — MCP server reputation",
    description: SITE_DESCRIPTION,
  },
  robots: {
    index: true,
    follow: true,
  },
};

export const viewport: Viewport = {
  themeColor: "#0A0F0C",
};

// Static, site-wide facts — safe to declare once here rather than per page.
// Per-server Review structured data lives in servers/page.tsx instead,
// since the individual server identity isn't known until the client fetches
// its shard (see the comment in servers/layout.tsx).
const organizationJsonLd = {
  "@context": "https://schema.org",
  "@type": "Organization",
  name: "mcphound",
  url: SITE_URL,
  description: SITE_DESCRIPTION,
  sameAs: ["https://github.com/markdoyle4312-hash/mcphound", "https://pypi.org/project/mcphound/"],
};

const websiteJsonLd = {
  "@context": "https://schema.org",
  "@type": "WebSite",
  name: "mcphound",
  url: SITE_URL,
  description: SITE_DESCRIPTION,
};

export default function RootLayout({ children }: { children: ReactNode }) {
  let watchCount: number | null = null;
  try {
    watchCount = loadIndex().length;
  } catch {
    watchCount = null;
  }

  return (
    <html lang="en" className={`${mono.variable} ${publicSans.variable}`}>
      <head>
        <link
          rel="alternate"
          type="application/rss+xml"
          title="mcphound — newly flagged servers"
          href="/feed.xml"
        />
        <link
          rel="alternate"
          type="application/feed+json"
          title="mcphound — newly flagged servers"
          href="/feed.json"
        />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: jsonLdScript(organizationJsonLd) }}
        />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: jsonLdScript(websiteJsonLd) }}
        />
      </head>
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
              <NavLink href="/browse/1" activePrefix="/browse">
                Registry
              </NavLink>
              <NavLink href="/typosquats" activePrefix="/typosquats">
                Typosquats
              </NavLink>
            </nav>
          </div>
          {watchCount !== null && (
            <div className="border-t border-ink-800 bg-ink-950/60">
              <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-x-4 gap-y-2 px-6 py-1.5 font-mono text-[11px] text-paper-dim">
                <span className="flex items-center gap-2">
                  <span className="h-1.5 w-1.5 rounded-full bg-clear" aria-hidden />
                  <span>
                    {watchCount} server{watchCount === 1 ? "" : "s"} on watch
                  </span>
                </span>
                <SearchBox />
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
              <Link href="/faq" className="-my-3 inline-block py-3 transition-colors hover:text-signal">
                FAQ
              </Link>
              <a
                href="/feed.xml"
                className="-my-3 inline-block py-3 transition-colors hover:text-signal"
              >
                RSS
              </a>
              <a
                href="https://github.com/markdoyle4312-hash/mcphound"
                className="-my-3 inline-block py-3 transition-colors hover:text-signal"
              >
                Source
              </a>
              <a
                href="https://pypi.org/project/mcphound/"
                className="-my-3 inline-block py-3 transition-colors hover:text-signal"
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
