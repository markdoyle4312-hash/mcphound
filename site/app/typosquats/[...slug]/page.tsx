import Link from "next/link";
import { notFound } from "next/navigation";
import { loadTyposquatClusters } from "@/lib/data";
import { nameToPathSegments, pathSegmentsToName, serverHref } from "@/lib/slug";

export function generateStaticParams() {
  return loadTyposquatClusters().map((cluster) => ({
    slug: nameToPathSegments(cluster.known_name),
  }));
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
      <h1 className="text-2xl font-bold mb-6">{cluster.known_name}</h1>
      {cluster.neighbors.length === 0 ? (
        <p>No lookalikes found in the current registry snapshot.</p>
      ) : (
        <ul className="space-y-2">
          {cluster.neighbors.map((neighbor) => (
            <li key={neighbor.identifier} className="border border-slate-800 rounded p-4">
              <p className="font-mono">{neighbor.identifier}</p>
              <p className="text-sm text-slate-400">
                {neighbor.distance} edit{neighbor.distance === 1 ? "" : "s"} away · published as{" "}
                {neighbor.server_slug ? (
                  <Link href={serverHref(neighbor.server_name)} className="underline">
                    {neighbor.server_name}
                  </Link>
                ) : (
                  neighbor.server_name
                )}
              </p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
