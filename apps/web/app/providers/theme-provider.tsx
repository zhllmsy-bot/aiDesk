"use client";

import { useCallback, useEffect, useState } from "react";

const storageKey = "ai-desk.theme";
type Theme = "dawn" | "midnight";

function applyTheme(theme: Theme) {
  document.documentElement.dataset.theme = theme;
  document.body.dataset.theme = theme;
}

export function useTheme() {
  const [theme, setThemeState] = useState<Theme>("midnight");

  useEffect(() => {
    const stored = window.localStorage.getItem(storageKey) as Theme | null;
    const next = stored === "dawn" || stored === "midnight" ? stored : "midnight";
    setThemeState(next);
    applyTheme(next);
  }, []);

  const setTheme = useCallback((next: Theme) => {
    setThemeState(next);
    window.localStorage.setItem(storageKey, next);
    applyTheme(next);
  }, []);

  return { theme, setTheme };
}
