import { loadNewlyFlagged } from "@/lib/data";
import { serverHref } from "@/lib/slug";
import { escapeXml } from "@/lib/xml";

const SITE_URL = "https://mcphound.dev";

export const dynamic = "force-static";

export async function GET() {
  const entries = loadNewlyFlagged();

  const items = entries
    .map((entry) => {
      const url = `${SITE_URL}${serverHref(entry.name)}`;
      const crossedFrom =
        entry.previous_score === null ? "unscored" : String(entry.previous_score);
      const description = `Score crossed from ${crossedFrom} to ${entry.score} (${entry.finding_count} finding${entry.finding_count === 1 ? "" : "s"}).`;
      const pubDate = new Date(entry.computed_at).toUTCString();
      return `
    <item>
      <title>${escapeXml(entry.name)}</title>
      <link>${escapeXml(url)}</link>
      <guid isPermaLink="true">${escapeXml(url)}</guid>
      <pubDate>${pubDate}</pubDate>
      <description>${escapeXml(description)}</description>
    </item>`;
    })
    .join("");

  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>mcphound — newly flagged servers</title>
    <link>${SITE_URL}/</link>
    <description>MCP servers whose score just crossed below 100 on mcphound's nightly rescan.</description>
    <language>en</language>
    <atom:link xmlns:atom="http://www.w3.org/2005/Atom" href="${SITE_URL}/feed.xml" rel="self" type="application/rss+xml" />${items}
  </channel>
</rss>
`;

  return new Response(xml, {
    headers: { "Content-Type": "application/rss+xml; charset=utf-8" },
  });
}
