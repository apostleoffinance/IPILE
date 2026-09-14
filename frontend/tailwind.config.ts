import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "var(--color-bg-canvas)",
        surface: "var(--color-bg-surface)",
        subtle: "var(--color-bg-subtle)",
        brand: "var(--color-bg-brand)",
        ink: "var(--color-text-primary)",
        muted: "var(--color-text-secondary)",
        accent: "var(--color-accent-primary)",
        "accent-deep": "var(--color-accent-deep)",
        gold: "var(--color-accent-gold)",
        "gold-bright": "var(--color-accent-gold-bright)",
        healthy: "var(--color-status-healthy)",
        warning: "var(--color-status-warning)",
        critical: "var(--color-status-critical)",
        line: "var(--color-border)",
      },
      borderRadius: {
        md: "12px",
      },
      fontFamily: {
        sans: ["var(--font-sans)"],
        display: ["var(--font-display)"],
      },
    },
  },
  plugins: [],
};

export default config;
