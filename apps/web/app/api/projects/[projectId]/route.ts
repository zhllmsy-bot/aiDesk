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

export async function GET(_request: Request, context: { params: Promise<{ projectId: string }> }) {
  const { projectId } = await context.params;
  const backendResponse = await getProjectDetailViaControlPlane(projectId);
  if (backendResponse) {
    return NextResponse.json(backendResponse);
  }

  const response = getWorkspaceProjectDetailResponse(projectId);

  if (!response) {
    return NextResponse.json({ message: "Project not found." }, { status: 404 });
  }

  return NextResponse.json(response);
}

export async function PATCH(request: Request, context: { params: Promise<{ projectId: string }> }) {
  const { projectId } = await context.params;
  const payload = (await request.json()) as {
    name: string;
    default_branch: string;
    description?: string | null;
  };

  const backendResponse = await updateProjectViaControlPlane(projectId, payload);
  if (backendResponse) {
    return NextResponse.json(backendResponse);
  }

  const updated = updateWorkspaceProject(projectId, payload);
  const detail = updated ? getWorkspaceProjectDetailResponse(projectId) : null;

  if (!detail) {
    return NextResponse.json({ message: "Project not found." }, { status: 404 });
  }

  return NextResponse.json(detail);
}

export async function DELETE(
  request: Request,
  context: { params: Promise<{ projectId: string }> },
) {
  const { projectId } = await context.params;
  const payload = (await request.json()) as {
    confirm_name: string;
  };

  const deleted = deleteWorkspaceProject(projectId, payload);

  if (!deleted) {
    return NextResponse.json(
      { message: "Project not found or confirmation mismatch." },
      { status: 400 },
    );
  }

  return NextResponse.json({ deleted: true });
}
