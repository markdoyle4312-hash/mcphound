import type { MetadataRoute } from "next";
import { loadIndex, loadTyposquatClusters, totalPages } from "@/lib/data";
import { serverHref, typosquatHref } from "@/lib/slug";

const SITE_URL = "https://mcphound.dev";

// Google's sitemap spec caps a single file at 50,000 URLs. The registry is
// ~28k servers today (see site/README.md) with room to grow — if entries +
// browse pages + typosquat clusters ever cross that line, switch this to
// Next's generateSitemaps() to split into multiple files.
const MAX_ENTRIES = 49_000;

export const dynamic = "force-static";

export default function sitemap(): MetadataRoute.Sitemap {
  const index = loadIndex();
  const clusters = loadTyposquatClusters();

  const entries: MetadataRoute.Sitemap = [
    { url: `${SITE_URL}/`, changeFrequency: "daily", priority: 1 },
    { url: `${SITE_URL}/typosquats`, changeFrequency: "daily", priority: 0.7 },
  ];

  const pages = totalPages(index);
  for (let page = 1; page <= pages; page += 1) {
    entries.push({
      url: `${SITE_URL}/browse/${page}`,
      changeFrequency: "daily",
      priority: page === 1 ? 0.8 : 0.5,
    });
  }

  for (const cluster of clusters) {
    entries.push({
      url: `${SITE_URL}${typosquatHref(cluster.known_name)}`,
      changeFrequency: "weekly",
      priority: 0.4,
    });
  }

  for (const entry of index) {
    entries.push({
      url: `${SITE_URL}${serverHref(entry.name)}`,
      lastModified: entry.last_scanned_at,
      changeFrequency: "daily",
      priority: entry.score < 100 ? 0.6 : 0.3,
    });
  }

  return entries.slice(0, MAX_ENTRIES);
}
