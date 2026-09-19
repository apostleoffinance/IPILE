import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["selector", '[data-theme="dark"]'],
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
        inverse: "var(--color-text-inverse)",
        accent: "var(--color-accent-primary)",
        "accent-deep": "var(--color-accent-deep)",
        gold: "var(--color-accent-gold)",
        "gold-bright": "var(--color-accent-gold-bright)",
        healthy: "var(--color-status-healthy)",
        warning: "var(--color-status-warning)",
        critical: "var(--color-status-critical)",
        info: "var(--color-status-info)",
        line: "var(--color-border)",
        input: "var(--color-input-bg)",
        forest: "var(--color-deep-forest)",
      },
      borderRadius: {
        md: "var(--radius-md)",
      },
      boxShadow: {
        soft: "var(--shadow-sm)",
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
