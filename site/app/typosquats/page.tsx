import type { Metadata } from "next";
import Link from "next/link";
import { loadTyposquatClusters } from "@/lib/data";
import { typosquatHref } from "@/lib/slug";

export function generateMetadata(): Metadata {
  const clusters = loadTyposquatClusters();
  const withNeighbors = clusters.filter((c) => c.neighbors.length > 0);
  return {
    title: "Typosquat watchlist",
    description: `${withNeighbors.length} of ${clusters.length} known MCP packages have a one- or two-character lookalike published on the registry.`,
    alternates: { canonical: "/typosquats" },
  };
}

export default function TyposquatsIndexPage() {
  const clusters = loadTyposquatClusters();
  const withNeighbors = clusters.filter((c) => c.neighbors.length > 0);

  return (
    <div>
      <p className="eyebrow mb-3">lookalike watchlist</p>
      <h1 className="mb-2 text-2xl font-semibold">
        {withNeighbors.length} of {clusters.length} known packages have a lookalike on the registry
      </h1>
      <p className="mb-8 max-w-2xl text-paper-dim">
        Each entry below is a package name that&rsquo;s one or two characters away from a
        well-known MCP server — the kind of edit a person skims past and a copy-paste doesn&rsquo;t
        catch.
      </p>

      {clusters.length === 0 ? (
        <p className="text-paper-dim">No known-package list loaded yet.</p>
      ) : (
        <ul className="divide-y divide-ink-800 border-y border-ink-700">
          {clusters.map((cluster) => (
            <li key={cluster.known_slug} className="flex items-center justify-between gap-6 py-3.5">
              <Link
                href={typosquatHref(cluster.known_name)}
                className="font-mono text-sm text-paper underline decoration-ink-700 underline-offset-4 hover:decoration-signal"
              >
                {cluster.known_name}
              </Link>
              <span
                className={`font-mono text-xs ${
                  cluster.neighbors.length > 0 ? "text-signal" : "text-paper-dim"
                }`}
              >
                {cluster.neighbors.length} lookalike{cluster.neighbors.length === 1 ? "" : "s"}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
