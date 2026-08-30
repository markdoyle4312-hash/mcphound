import Link from "next/link";
import { flaggedServers, loadIndex } from "@/lib/data";
import { serverHref } from "@/lib/slug";

export default function HomePage() {
  const flagged = flaggedServers(loadIndex());

  return (
    <div>
      <h1 className="text-2xl font-bold mb-2">Flagged MCP servers</h1>
      <p className="text-slate-400 mb-6">
        {flagged.length} server{flagged.length === 1 ? "" : "s"} scored below 100, worst first.{" "}
        <Link href="/browse/1" className="underline">
          Browse all scanned servers
        </Link>
        .
      </p>
      <table className="w-full text-left border-collapse">
        <thead>
          <tr className="border-b border-slate-800 text-slate-400">
            <th className="py-2">Server</th>
            <th className="py-2">Score</th>
            <th className="py-2">Findings</th>
          </tr>
        </thead>
        <tbody>
          {flagged.map((entry) => (
            <tr key={entry.slug} className="border-b border-slate-900">
              <td className="py-2">
                <Link href={serverHref(entry.name)} className="underline">
                  {entry.name}
                </Link>
              </td>
              <td className="py-2">{entry.score}</td>
              <td className="py-2">{entry.finding_count}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
