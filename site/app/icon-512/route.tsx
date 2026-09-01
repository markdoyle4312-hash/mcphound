import { ImageResponse } from "next/og";

// See app/icon-192/route.tsx for why this exists as a plain generated
// route instead of a Next icon-file convention.
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
          borderRadius: 112,
        }}
      >
        <svg width="307" height="307" viewBox="0 0 32 32">
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
    { width: 512, height: 512 }
  );
}
