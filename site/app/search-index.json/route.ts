import { loadIndex } from "@/lib/data";

// Compact [name, score] tuples rather than {name, score} objects — at
// registry scale (~28k servers) that drops the repeated key names, which
// is most of what gzip/brotli can't already squeeze out of this file.
// Fetched lazily by components/SearchBox.tsx, only once the search box
// is actually used, not on every page load.
export const dynamic = "force-static";

export async function GET() {
  const index = loadIndex();
  const compact = index.map((entry) => [entry.name, entry.score]);
  return Response.json(compact);
}
