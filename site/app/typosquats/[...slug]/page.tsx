import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { loadTyposquatClusters } from "@/lib/data";
import { nameToPathSegments, pathSegmentsToName, serverHref } from "@/lib/slug";
import { IdentifierDiff } from "@/components/IdentifierDiff";

export function generateStaticParams() {
  return loadTyposquatClusters().map((cluster) => ({
    slug: nameToPathSegments(cluster.known_name),
  }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string[] }>;
}): Promise<Metadata> {
  const { slug: pathSegments } = await params;
  const name = pathSegmentsToName(pathSegments);
  const cluster = loadTyposquatClusters().find((c) => c.known_name === name);
  if (!cluster) {
    return { title: "Typosquat lookup" };
  }
  return {
    title: cluster.known_name,
    description:
      cluster.neighbors.length === 0
        ? `No lookalike package names found for ${cluster.known_name} in the current registry snapshot.`
        : `${cluster.neighbors.length} lookalike${cluster.neighbors.length === 1 ? "" : "s"} of ${cluster.known_name} found on the registry, with the exact characters that differ.`,
  };
}

export default async function TyposquatDetailPage({
  params,
}: {
  params: Promise<{ slug: string[] }>;
}) {
  const { slug: pathSegments } = await params;
  const name = pathSegmentsToName(pathSegments);
  const cluster = loadTyposquatClusters().find((c) => c.known_name === name);
  if (!cluster) {
    notFound();
  }

  return (
    <div>
      <p className="eyebrow mb-3">known package</p>
      <h1 className="mb-8 break-all font-mono text-2xl font-semibold">{cluster.known_name}</h1>

      {cluster.neighbors.length === 0 ? (
        <p className="text-clear">No lookalikes found in the current registry snapshot.</p>
      ) : (
        <ul className="space-y-4">
          {cluster.neighbors.map((neighbor) => (
            <li key={neighbor.identifier} className="border border-ink-700 bg-ink-900 p-5">
              <IdentifierDiff known={cluster.known_name} lookalike={neighbor.identifier} />
              <p className="mt-4 border-t border-ink-800 pt-3 font-mono text-xs text-paper-dim">
                {neighbor.distance} edit{neighbor.distance === 1 ? "" : "s"} away · published as{" "}
                {neighbor.server_slug ? (
                  <Link
                    href={serverHref(neighbor.server_name)}
                    className="text-paper underline hover:text-signal"
                  >
                    {neighbor.server_name}
                  </Link>
                ) : (
                  <span className="text-paper">{neighbor.server_name}</span>
                )}
              </p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
