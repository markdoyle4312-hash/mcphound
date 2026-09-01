import type { MetadataRoute } from "next";

export const dynamic = "force-static";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "mcphound — MCP server reputation",
    short_name: "mcphound",
    description: "Independent security scores for public Model Context Protocol servers.",
    start_url: "/",
    display: "standalone",
    background_color: "#0A0F0C",
    theme_color: "#0A0F0C",
    icons: [
      { src: "/icon-192", sizes: "192x192", type: "image/png" },
      { src: "/icon-512", sizes: "512x512", type: "image/png" },
    ],
  };
}
