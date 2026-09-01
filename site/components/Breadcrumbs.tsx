import Link from "next/link";
import { jsonLdScript } from "@/lib/jsonld";

const SITE_URL = "https://mcphound.dev";

export type Crumb = { label: string; href?: string };

/** Visible trail + matching BreadcrumbList JSON-LD, for pages nested two
 * levels deep (typosquat detail, server detail) where the URL alone
 * doesn't make the hierarchy obvious. */
export function Breadcrumbs({ items }: { items: Crumb[] }) {
  const breadcrumbJsonLd = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: items.map((item, i) => ({
      "@type": "ListItem",
      position: i + 1,
      name: item.label,
      ...(item.href ? { item: `${SITE_URL}${item.href}` } : {}),
    })),
  };

  return (
    <nav aria-label="Breadcrumb" className="mb-6">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: jsonLdScript(breadcrumbJsonLd) }}
      />
      <ol className="flex flex-wrap items-center gap-x-2 font-mono text-xs text-paper-dim">
        {items.map((item, i) => (
          <li key={item.label} className="flex items-center gap-x-2">
            {i > 0 && <span aria-hidden>/</span>}
            {item.href ? (
              <Link href={item.href} className="underline decoration-ink-700 hover:decoration-signal hover:text-signal">
                {item.label}
              </Link>
            ) : (
              <span aria-current="page" className="text-paper">
                {item.label}
              </span>
            )}
          </li>
        ))}
      </ol>
    </nav>
  );
}
