"use client";

import { useTheme } from "@/app/providers/theme-provider";
import { Button } from "@ai-desk/ui";

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  const next = theme === "midnight" ? "dawn" : "midnight";

  return (
    <Button tone="secondary" onClick={() => setTheme(next)}>
      {theme === "midnight" ? "Night" : "Dawn"}
    </Button>
  );
}
