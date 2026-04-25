import type { ApiClient, ApiSchemas } from "@ai-desk/contracts-api";
import { createApiClient } from "@ai-desk/contracts-api";

import { createWorkspaceSession } from "@/features/access/session";

const DEV_EMAIL = "admin@example.com";
const DEV_PASSWORD = "super-secure-password";
const DEV_DISPLAY_NAME = "Admin Operator";

type SessionContextResponse = ApiSchemas["SessionContextResponse"];

let cachedSession: SessionContextResponse | null = null;

function resolveApiBaseUrl() {
  return process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ?? "";
}

function sessionIsUsable(session: SessionContextResponse | null) {
  if (!session) {
    return false;
  }

  return new Date(session.session.expires_at).getTime() > Date.now() + 30_000;
}

async function issueDevApiSession(client: ApiClient): Promise<SessionContextResponse> {
  const registerResult = await client.POST("/auth/register", {
    body: {
      email: DEV_EMAIL,
      password: DEV_PASSWORD,
      display_name: DEV_DISPLAY_NAME,
    },
  });

  if (registerResult.data) {
    return registerResult.data;
  }

  if (registerResult.response.status !== 409) {
    throw new Error("Failed to bootstrap development API session.");
  }

  const sessionResult = await client.POST("/auth/sessions", {
    body: {
      email: DEV_EMAIL,
      password: DEV_PASSWORD,
    },
  });

  if (!sessionResult.data) {
    throw new Error("Failed to authenticate development API session.");
  }

  return sessionResult.data;
}

export async function getServerApiClient(): Promise<{
  apiSession: SessionContextResponse;
  client: ApiClient;
} | null> {
  const baseUrl = resolveApiBaseUrl();
  if (!baseUrl) {
    return null;
  }

  try {
    if (!sessionIsUsable(cachedSession)) {
      const bootstrapClient = createApiClient({ baseUrl });
      cachedSession = await issueDevApiSession(bootstrapClient);
    }

    if (!cachedSession) {
      return null;
    }

    return {
      apiSession: cachedSession,
      client: createApiClient({
        baseUrl,
        headers: {
          Authorization: `Bearer ${cachedSession.session.token}`,
        },
      }),
    };
  } catch {
    cachedSession = null;
    return null;
  }
}

export function createFallbackWorkspaceSession() {
  return createWorkspaceSession({
    display_name: DEV_DISPLAY_NAME,
    email: DEV_EMAIL,
    role: "admin",
    active_project_id: "proj_atlas",
  });
}
