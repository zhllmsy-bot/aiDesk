import { NextResponse } from "next/server";

import {
  getProjectDetailViaControlPlane,
  updateProjectViaControlPlane,
} from "@/features/projects/server/control-plane-proxy";
import {
  deleteWorkspaceProject,
  getWorkspaceProjectDetailResponse,
  updateWorkspaceProject,
} from "@/features/projects/server/project-store";

type ProjectRouteContext = { params: Promise<{ projectId: string }> };
type ProjectUpdatePayload = {
  name: string;
  default_branch: string;
  description?: string | null;
};

function projectNotFound() {
  return NextResponse.json({ message: "Project not found." }, { status: 404 });
}

export async function GET(_request: Request, context: { params: Promise<{ projectId: string }> }) {
  const { projectId } = await context.params;
  const backendResponse = await getProjectDetailViaControlPlane(projectId);
  if (backendResponse) {
    return NextResponse.json(backendResponse);
  }
  const response = getWorkspaceProjectDetailResponse(projectId);
  return response ? NextResponse.json(response) : projectNotFound();
}

export async function PATCH(request: Request, context: ProjectRouteContext) {
  const { projectId } = await context.params;
  const payload = (await request.json()) as ProjectUpdatePayload;
  const backendResponse = await updateProjectViaControlPlane(projectId, payload);
  if (backendResponse) {
    return NextResponse.json(backendResponse);
  }
  const updated = updateWorkspaceProject(projectId, payload);
  const detail = updated ? getWorkspaceProjectDetailResponse(projectId) : null;
  return detail ? NextResponse.json(detail) : projectNotFound();
}

export async function DELETE(request: Request, context: ProjectRouteContext) {
  const { projectId } = await context.params;
  const payload = (await request.json()) as { confirm_name: string };
  const deleted = deleteWorkspaceProject(projectId, payload);
  if (!deleted) {
    return NextResponse.json(
      { message: "Project not found or confirmation mismatch." },
      { status: 400 },
    );
  }

  return NextResponse.json({ deleted: true });
}
