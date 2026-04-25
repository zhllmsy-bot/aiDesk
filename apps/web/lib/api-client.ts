import { createApiClient } from "@ai-desk/contracts-api";
import type { WorkspaceSession } from "@ai-desk/contracts-projects";

import { sessionStorageKey } from "@/features/access/storage";

type StoredWorkspaceSession = WorkspaceSession & {
  api_token?: string | null;
  api_session_id?: string | null;
  api_expires_at?: string | null;
};

const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";
const webApiClient = createApiClient({ baseUrl });

let devSessionBootstrap: Promise<StoredWorkspaceSession | null> | null = null;

function isBrowser() {
  return typeof window !== "undefined";
}

function readStoredSession(): StoredWorkspaceSession | null {
  if (!isBrowser()) {
    return null;
  }

  try {
    const raw = window.sessionStorage.getItem(sessionStorageKey);
    return raw ? (JSON.parse(raw) as StoredWorkspaceSession) : null;
  } catch {
    return null;
  }
}

async function bootstrapDevSession(): Promise<StoredWorkspaceSession | null> {
  if (!isBrowser() || process.env.NODE_ENV !== "development") {
    return readStoredSession();
  }

  if (devSessionBootstrap) {
    return devSessionBootstrap;
  }

  devSessionBootstrap = (async () => {
    const response = await fetch("/api/dev/session", {
      method: "POST",
      cache: "no-store",
    });

    if (!response.ok) {
      return readStoredSession();
    }

    const session = (await response.json()) as StoredWorkspaceSession;
    window.sessionStorage.setItem(sessionStorageKey, JSON.stringify(session));
    return session;
  })().finally(() => {
    devSessionBootstrap = null;
  });

  return devSessionBootstrap;
}

export async function getApiHeaders(headers?: HeadersInit): Promise<HeadersInit | undefined> {
  const merged = new Headers(headers);
  let session = readStoredSession();

  if (!session?.api_token) {
    session = await bootstrapDevSession();
  }

  if (session?.api_token) {
    merged.set("Authorization", `Bearer ${session.api_token}`);
  }

  return merged;
}

export function getApiErrorMessage(payload: unknown, status: number): string {
  if (payload && typeof payload === "object") {
    const detail = "detail" in payload ? payload.detail : null;
    if (typeof detail === "string" && detail.length > 0) {
      return detail;
    }

    const message = "message" in payload ? payload.message : null;
    if (typeof message === "string" && message.length > 0) {
      return message;
    }
  }

  return `Request failed with status ${status}`;
}

export { webApiClient };
