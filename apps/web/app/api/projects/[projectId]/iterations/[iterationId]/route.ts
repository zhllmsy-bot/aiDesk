import { NextResponse } from "next/server";

import { getIterationPageViaControlPlane } from "@/features/projects/server/control-plane-proxy";
import { getWorkspaceIterationPageResponse } from "@/features/projects/server/project-store";

export async function GET(
  _request: Request,
  context: { params: Promise<{ projectId: string; iterationId: string }> },
) {
  const { projectId, iterationId } = await context.params;
  const backendResponse = await getIterationPageViaControlPlane(projectId, iterationId);
  if (backendResponse) {
    return NextResponse.json(backendResponse);
  }

  const response = getWorkspaceIterationPageResponse(projectId, iterationId);

  if (!response) {
    return NextResponse.json({ message: "Iteration not found." }, { status: 404 });
  }

  return NextResponse.json(response);
}
