import { notFound } from "next/navigation";
import { loadIndex, loadServer } from "@/lib/data";
import { nameToPathSegments, pathSegmentsToName } from "@/lib/slug";

export function generateStaticParams() {
  return loadIndex().map((entry) => ({ slug: nameToPathSegments(entry.name) }));
}

export default async function ServerPage({
  params,
}: {
  params: Promise<{ slug: string[] }>;
}) {
  const { slug: pathSegments } = await params;
  const name = pathSegmentsToName(pathSegments);
  const entry = loadIndex().find((e) => e.name === name);
  if (!entry) {
    notFound();
  }
  const server = loadServer(entry.slug);

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
