"use client";

import { useEffect, useState } from "react";
import { pathSegmentsToName } from "@/lib/slug";
import { shardKey } from "@/lib/shard";
import type { ServerDetail } from "@/lib/types";

type State =
  | { status: "loading" }
  | { status: "not-found" }
  | { status: "error" }
  | { status: "ready"; server: ServerDetail };

export default function ServerPage() {
  const [state, setState] = useState<State>({ status: "loading" });

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
    return <p>Loading…</p>;
  }
  if (state.status === "not-found") {
    return <p>Server not found.</p>;
  }
  if (state.status === "error") {
    return <p>Failed to load server data.</p>;
  }

  const { server } = state;
  return (
    <div>
      <h1 className="text-2xl font-bold mb-1">{server.name}</h1>
      <p className="text-slate-400 mb-6">
        Score {server.score} · {server.finding_count} finding
        {server.finding_count === 1 ? "" : "s"} · last scanned {server.computed_at}
      </p>
      {server.findings.length === 0 ? (
        <p>No findings.</p>
      ) : (
        <ul className="space-y-4">
          {server.findings.map((finding) => (
            <li key={finding.rule_id} className="border border-slate-800 rounded p-4">
              <p className="font-semibold">
                {finding.title}{" "}
                <span className="text-slate-500 font-normal">
                  ({finding.rule_id}, {finding.owasp})
                </span>
              </p>
              <p className="text-sm text-slate-400">
                Severity: {finding.severity} · Confidence: {finding.confidence}
              </p>
              <p className="mt-2">{finding.detail}</p>
              {finding.recommendation && (
                <p className="mt-2 text-slate-400">{finding.recommendation}</p>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
