import { AuditCanvasScreen } from "@/features/projects/components/audit-canvas-screen";

export default async function ProjectAuditPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = await params;
  return <AuditCanvasScreen projectId={projectId} />;
}
