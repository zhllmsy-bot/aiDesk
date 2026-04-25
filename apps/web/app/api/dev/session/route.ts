import { NextResponse } from "next/server";

import { createFallbackWorkspaceSession, getServerApiClient } from "@/lib/server-api-client";

export async function POST() {
  const fallback = createFallbackWorkspaceSession();

  try {
    const serverApi = await getServerApiClient();
    if (!serverApi) {
      return NextResponse.json(fallback);
    }

    return NextResponse.json({
      ...fallback,
      api_token: serverApi.apiSession.session.token,
      api_session_id: serverApi.apiSession.session.id,
      api_expires_at: serverApi.apiSession.session.expires_at,
    });
  } catch {
    return NextResponse.json(fallback);
  }
}
