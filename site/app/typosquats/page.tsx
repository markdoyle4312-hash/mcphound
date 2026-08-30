import Link from "next/link";
import { loadTyposquatClusters } from "@/lib/data";
import { typosquatHref } from "@/lib/slug";

export default function TyposquatsIndexPage() {
  const clusters = loadTyposquatClusters();

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Typosquat watchlist</h1>
      <ul className="space-y-2">
        {clusters.map((cluster) => (
          <li key={cluster.known_slug}>
            <Link href={typosquatHref(cluster.known_name)} className="underline">
              {cluster.known_name}
            </Link>{" "}
            <span className="text-slate-500">
              ({cluster.neighbors.length} lookalike{cluster.neighbors.length === 1 ? "" : "s"})
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
