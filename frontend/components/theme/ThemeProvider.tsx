"use client";

import { useEffect, useState } from "react";
import { applyTheme, resolveTheme, setTheme, type Theme } from "@/lib/theme";

/** Syncs document theme after hydration; blocking script in layout prevents FOUC. */
export function ThemeProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    applyTheme(resolveTheme());
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => {
      if (!window.localStorage.getItem("ipile_theme")) {
        applyTheme(media.matches ? "dark" : "light");
      }
    };
    media.addEventListener("change", onChange);
    return () => media.removeEventListener("change", onChange);
  }, []);

  return <>{children}</>;
}

export function useTheme() {
  const [theme, setThemeState] = useState<Theme>("light");

  useEffect(() => {
    setThemeState(resolveTheme());
  }, []);

  function choose(next: Theme) {
    setTheme(next);
    setThemeState(next);
  }

  function toggle() {
    choose(theme === "dark" ? "light" : "dark");
  }

  return { theme, setTheme: choose, toggle };
}
