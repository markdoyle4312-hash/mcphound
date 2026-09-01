import { loadNewlyFlagged } from "@/lib/data";
import { serverHref } from "@/lib/slug";

const SITE_URL = "https://mcphound.dev";

export const dynamic = "force-static";

export async function GET() {
  const entries = loadNewlyFlagged();

  const feed = {
    version: "https://jsonfeed.org/version/1.1",
    title: "mcphound — newly flagged servers",
    home_page_url: `${SITE_URL}/`,
    feed_url: `${SITE_URL}/feed.json`,
    description: "MCP servers whose score just crossed below 100 on mcphound's nightly rescan.",
    items: entries.map((entry) => {
      const url = `${SITE_URL}${serverHref(entry.name)}`;
      const crossedFrom =
        entry.previous_score === null ? "unscored" : String(entry.previous_score);
      return {
        id: url,
        url,
        title: entry.name,
        content_text: `Score crossed from ${crossedFrom} to ${entry.score} (${entry.finding_count} finding${entry.finding_count === 1 ? "" : "s"}).`,
        date_published: entry.computed_at,
      };
    }),
  };

  return Response.json(feed, {
    headers: { "Content-Type": "application/feed+json; charset=utf-8" },
  });
}
