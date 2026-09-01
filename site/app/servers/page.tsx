"use client";

import { useEffect, useState } from "react";
import { pathSegmentsToName, serverHref } from "@/lib/slug";
import { shardKey } from "@/lib/shard";
import { jsonLdScript } from "@/lib/jsonld";
import type { ServerDetail } from "@/lib/types";
import { ScoreCascade } from "@/components/ScoreCascade";
import { SeverityBadge } from "@/components/SeverityBadge";

const SITE_URL = "https://mcphound.dev";

// The static export can't give /servers/<name> its own prerendered <title>,
// canonical link, or structured data (see servers/layout.tsx) — this fills
// all three in once the client has the real server identity, so search
// engines that render the page still see per-server signals, not the one
// generic shell.
function useServerHead(server: ServerDetail | null) {
  useEffect(() => {
    if (!server) return;

    const previousTitle = document.title;
    document.title = `${server.name} · mcphound`;

    const canonical = document.createElement("link");
    canonical.rel = "canonical";
    canonical.href = `${SITE_URL}${serverHref(server.name)}`;
    document.head.appendChild(canonical);

    const reviewJsonLd = {
      "@context": "https://schema.org",
      "@type": "Review",
      itemReviewed: {
        "@type": "SoftwareApplication",
        name: server.name,
        applicationCategory: "MCP server",
      },
      author: { "@type": "Organization", name: "mcphound" },
      reviewRating: {
        "@type": "Rating",
        ratingValue: server.score,
        bestRating: 100,
        worstRating: 0,
      },
      datePublished: server.computed_at,
    };
    const script = document.createElement("script");
    script.type = "application/ld+json";
    script.text = jsonLdScript(reviewJsonLd);
    document.head.appendChild(script);

    return () => {
      document.title = previousTitle;
      canonical.remove();
      script.remove();
    };
  }, [server]);
}

type State =
  | { status: "loading" }
  | { status: "not-found" }
  | { status: "error" }
  | { status: "ready"; server: ServerDetail };

export default function ServerPage() {
  const [state, setState] = useState<State>({ status: "loading" });
  useServerHead(state.status === "ready" ? state.server : null);

  useEffect(() => {
    let cancelled = false;
    const segments = window.location.pathname
      .replace(/^\/servers\/?/, "")
      .split("/")
      .filter(Boolean);
    const name = segments.length > 0 ? pathSegmentsToName(segments) : null;

    (async () => {
      if (!name) {
        if (!cancelled) setState({ status: "not-found" });
        return;
      }
      try {
        const res = await fetch(`/data/shard-${shardKey(name)}.json`);
        if (!res.ok) throw new Error(`shard fetch failed: ${res.status}`);
        const data = (await res.json()) as Record<string, ServerDetail>;
        if (cancelled) return;
        const server = data[name];
        setState(server ? { status: "ready", server } : { status: "not-found" });
      } catch {
        if (!cancelled) setState({ status: "error" });
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  if (state.status === "loading") {
    return <p className="font-mono text-sm text-paper-dim">Loading case file…</p>;
  }
  if (state.status === "not-found") {
    return <p className="font-mono text-sm text-paper-dim">Server not found.</p>;
  }
  if (state.status === "error") {
    return <p className="font-mono text-sm text-sev-high">Failed to load server data.</p>;
  }

  const { server } = state;

  return (
    <div>
      <p className="eyebrow mb-3">case file</p>
      <h1 className="mb-1 break-all font-mono text-2xl font-semibold">{server.name}</h1>
      <p className="mb-8 font-mono text-xs text-paper-dim">
        last scanned {server.computed_at.slice(0, 10)}
      </p>

      <div className="mb-10">
        <ScoreCascade findings={server.findings} />
      </div>

      {server.findings.length > 0 && (
        <>
          <p className="eyebrow mb-3">findings</p>
          <ul className="space-y-4">
            {server.findings.map((finding) => (
              <li key={finding.rule_id} className="border border-ink-700 bg-ink-900 p-5">
                <div className="mb-2 flex flex-wrap items-center gap-2">
                  <SeverityBadge severity={finding.severity} />
                  <span className="font-mono text-xs text-paper-dim">
                    confidence: {finding.confidence}
                  </span>
                  <span className="font-mono text-xs text-paper-dim">·</span>
                  <span className="font-mono text-xs text-paper-dim">{finding.owasp}</span>
                  <span className="ml-auto font-mono text-xs text-paper-dim">
                    {finding.rule_id}
                  </span>
                </div>
                <p className="font-semibold text-paper">{finding.title}</p>
                <p className="mt-2 text-sm text-paper-dim">{finding.detail}</p>
                {finding.recommendation && (
                  <p className="mt-3 border-t border-ink-800 pt-3 text-sm text-paper">
                    {finding.recommendation}
                  </p>
                )}
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
