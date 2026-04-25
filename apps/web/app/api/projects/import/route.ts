import { NextResponse } from "next/server";

import { importProjectViaControlPlane } from "@/features/projects/server/control-plane-proxy";
import {
  createWorkspaceProject,
  getWorkspaceProjectDetailResponse,
} from "@/features/projects/server/project-store";

export async function POST(request: Request) {
  const payload = (await request.json()) as {
    name: string;
    root_path: string;
    default_branch: string;
    description?: string | null;
  };

  if (!payload.root_path.startsWith("/")) {
    return NextResponse.json({ message: "rootPath must be an absolute path." }, { status: 400 });
  }

  const backendResponse = await importProjectViaControlPlane(payload);
  if (backendResponse) {
    return NextResponse.json(backendResponse, { status: 201 });
  }

  const item = createWorkspaceProject(payload);
  const detail = getWorkspaceProjectDetailResponse(item.id);
  return NextResponse.json(detail, { status: 201 });
}
