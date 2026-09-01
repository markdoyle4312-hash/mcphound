import { ImageResponse } from "next/og";

// One shared image for the whole site. Server detail pages are a
// client-rendered shell (see site/README.md's "Deployment" section — one
// static route per server blew past Cloudflare Pages' file cap), so a
// build-time per-server image isn't available; every page falls back to
// this one via Next's file-convention inheritance.
export const alt = "mcphound — MCP server reputation";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";
export const dynamic = "force-static";

const INK_950 = "#0A0F0C";
const INK_800 = "#1A2319";
const INK_700 = "#28352A";
const PAPER = "#EDE7D8";
const PAPER_DIM = "#98A395";
const SIGNAL = "#FF6A2B";
const CLEAR = "#6FCF97";

export default function Image() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          backgroundColor: INK_950,
          backgroundImage: `repeating-linear-gradient(0deg, ${INK_800} 0px, ${INK_800} 1px, transparent 1px, transparent 44px)`,
          padding: "72px 84px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 18 }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              width: 64,
              height: 64,
              borderRadius: 14,
              backgroundColor: INK_950,
              border: `2px solid ${INK_700}`,
            }}
          >
            <svg width="34" height="34" viewBox="0 0 32 32">
              <path
                d="M10 9 L18 16 L10 23"
                fill="none"
                stroke={SIGNAL}
                strokeWidth={3.6}
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <circle cx="24" cy="24" r="3.2" fill={CLEAR} />
            </svg>
          </div>
          <span
            style={{
              fontSize: 30,
              letterSpacing: "0.22em",
              textTransform: "uppercase",
              color: PAPER_DIM,
            }}
          >
            night watch over the MCP registry
          </span>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 22 }}>
          <span style={{ fontSize: 130, fontWeight: 700, color: PAPER, letterSpacing: "-0.02em" }}>
            mcphound
          </span>
          <span style={{ fontSize: 32, color: PAPER_DIM, maxWidth: 900 }}>
            Independent security scores for public Model Context Protocol servers.
          </span>
        </div>

        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 14,
            borderTop: `2px solid ${INK_700}`,
            paddingTop: 28,
          }}
        >
          <div style={{ width: 12, height: 12, borderRadius: 6, backgroundColor: CLEAR }} />
          <span style={{ fontSize: 26, color: PAPER_DIM }}>
            Static analysis only — mcphound never executes a server to score it.
          </span>
        </div>
      </div>
    ),
    { ...size }
  );
}
