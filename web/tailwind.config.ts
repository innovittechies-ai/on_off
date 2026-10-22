import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#0a0f1a",
          900: "#111827",
          800: "#1e293b",
          700: "#334155",
        },
        accent: {
          DEFAULT: "#c9a227",
          light: "#e8c547",
          muted: "#8b7355",
        },
        surface: {
          DEFAULT: "rgba(255,255,255,0.06)",
          hover: "rgba(255,255,255,0.1)",
          border: "rgba(255,255,255,0.12)",
        },
      },
      fontFamily: {
        sans: ["var(--font-dm-sans)", "system-ui", "sans-serif"],
        display: ["var(--font-fraunces)", "Georgia", "serif"],
      },
      boxShadow: {
        glow: "0 0 60px rgba(201, 162, 39, 0.15)",
        card: "0 4px 24px rgba(0,0,0,0.35)",
      },
    },
  },
  plugins: [],
};

export default config;
