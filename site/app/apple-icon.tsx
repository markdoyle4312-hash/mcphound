import { ImageResponse } from "next/og";

// Auto-detected by Next and wired up as <link rel="apple-touch-icon">. Safari
// on iOS ignores the regular <link rel="icon"> SVG entirely, so without this
// file a home-screen bookmark gets a generic screenshot instead of the mark.
export const size = { width: 180, height: 180 };
export const contentType = "image/png";
export const dynamic = "force-static";

export default function AppleIcon() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          backgroundColor: "#0A0F0C",
        }}
      >
        {/* iOS applies its own corner rounding, so this stays a plain
            square with the glyph centered and padded, not pre-rounded. */}
        <svg width="108" height="108" viewBox="0 0 32 32">
          <path
            d="M10 9 L18 16 L10 23"
            fill="none"
            stroke="#FF6A2B"
            strokeWidth={3.6}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <circle cx="24" cy="24" r="3.2" fill="#6FCF97" />
        </svg>
      </div>
    ),
    { ...size }
  );
}
