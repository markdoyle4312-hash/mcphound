import { ImageResponse } from "next/og";

// PWA manifest icon — Android's install/maskable icon slots require a raster
// PNG (no SVG), hence a separate generated route rather than reusing
// app/icon.svg. Not a Next file-convention name, so it's referenced
// directly from manifest.ts's icons array.
export const dynamic = "force-static";

export async function GET() {
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
          borderRadius: 42,
        }}
      >
        <svg width="115" height="115" viewBox="0 0 32 32">
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
    { width: 192, height: 192 }
  );
}
