"use client";

import { useEffect } from "react";

import { sessionStorageKey } from "@/features/access/storage";
import { createFallbackWorkspaceSession } from "@/lib/server-api-client";

export function DevSessionBootstrap() {
  useEffect(() => {
    if (process.env.NODE_ENV !== "development") {
      return;
    }

    let cancelled = false;

    const bootstrap = async () => {
      try {
        if (window.sessionStorage.getItem(sessionStorageKey)) {
          return;
        }

        const response = await fetch("/api/dev/session", {
          method: "POST",
          cache: "no-store",
        });
        const payload = response.ok ? await response.json() : createFallbackWorkspaceSession();

        if (!cancelled) {
          window.sessionStorage.setItem(sessionStorageKey, JSON.stringify(payload));
        }
      } catch {
        if (!cancelled) {
          window.sessionStorage.setItem(
            sessionStorageKey,
            JSON.stringify(createFallbackWorkspaceSession()),
          );
        }
      }
    };

    try {
      void bootstrap();
    } catch {
      // Ignore session storage bootstrap failures in non-browser or restricted contexts.
    }

    return () => {
      cancelled = true;
    };
  }, []);

  return null;
}
