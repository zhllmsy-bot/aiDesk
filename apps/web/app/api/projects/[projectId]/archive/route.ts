import { NextResponse } from "next/server";

import {
  archiveProjectViaControlPlane,
  getProjectDetailViaControlPlane,
} from "@/features/projects/server/control-plane-proxy";
import {
  archiveWorkspaceProject,
  getWorkspaceProjectDetailResponse,
} from "@/features/projects/server/project-store";

export async function POST(request: Request, context: { params: Promise<{ projectId: string }> }) {
  const { projectId } = await context.params;
  const payload = (await request.json()) as {
    confirm_name: string;
  };

  const existing = await getWorkspaceProjectDetailResponse(projectId);
  const backendCurrent = await getProjectDetailViaControlPlane(projectId);
  const expectedName = backendCurrent?.item.project.name ?? existing?.item.project.name ?? null;
  if (expectedName && payload.confirm_name !== expectedName) {
    return NextResponse.json(
      { message: "Project not found or confirmation mismatch." },
      { status: 400 },
    );
  }

  const backendResponse = await archiveProjectViaControlPlane(projectId);
  if (backendResponse) {
    return NextResponse.json(backendResponse);
  }

  const archived = archiveWorkspaceProject(projectId, payload);
  const detail = archived ? getWorkspaceProjectDetailResponse(projectId) : null;

  if (!detail) {
    return NextResponse.json(
      { message: "Project not found or confirmation mismatch." },
      { status: 400 },
    );
  }

  return NextResponse.json(detail);
}
