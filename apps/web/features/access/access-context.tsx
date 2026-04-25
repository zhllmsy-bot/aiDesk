"use client";

import { useCallback, useEffect, useState } from "react";

import type { WorkspaceSession } from "@ai-desk/contracts-projects";

import { createWorkspaceSession } from "./session";
import { sessionStorageKey } from "./storage";

const fallbackSession = createWorkspaceSession({
  display_name: "Admin Operator",
  email: "admin@example.com",
  role: "admin",
  active_project_id: "proj_atlas",
});

function readSession(): WorkspaceSession {
  if (typeof window === "undefined") {
    return fallbackSession;
  }

  try {
    const raw = window.sessionStorage.getItem(sessionStorageKey);
    return raw ? (JSON.parse(raw) as WorkspaceSession) : fallbackSession;
  } catch {
    return fallbackSession;
  }
}

export function useAccessSession() {
  const [session, setSession] = useState<WorkspaceSession>(fallbackSession);

  useEffect(() => {
    setSession(readSession());
  }, []);

  const signOut = useCallback(() => {
    if (typeof window !== "undefined") {
      window.sessionStorage.removeItem(sessionStorageKey);
    }
    setSession({ ...fallbackSession, is_authenticated: false });
  }, []);

  const signIn = useCallback(
    (input: {
      displayName: string;
      email: string;
      role: WorkspaceSession["roles"][number];
      activeProjectId?: string | null;
    }) => {
      const next = createWorkspaceSession({
        display_name: input.displayName,
        email: input.email,
        role: input.role,
        active_project_id: input.activeProjectId ?? null,
      });
      if (typeof window !== "undefined") {
        window.sessionStorage.setItem(sessionStorageKey, JSON.stringify(next));
      }
      setSession(next);
    },
    [],
  );

  return { session, signIn, signOut };
}
