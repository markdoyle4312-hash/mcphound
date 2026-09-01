import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#0A0F0C",
          900: "#111813",
          800: "#1A2319",
          700: "#28352A",
        },
        paper: {
          DEFAULT: "#EDE7D8",
          dim: "#98A395",
        },
        signal: {
          DEFAULT: "#FF6A2B",
          dim: "#B4501F",
        },
        clear: "#6FCF97",
        sev: {
          high: "#F0555B",
          medium: "#F0A93F",
          low: "#C9B98A",
        },
      },
      fontFamily: {
        mono: ["var(--font-mono)", "ui-monospace", "SFMono-Regular", "monospace"],
        sans: ["var(--font-sans)", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      letterSpacing: {
        widest2: "0.2em",
      },
    },
  },
  plugins: [],
};

export default config;
