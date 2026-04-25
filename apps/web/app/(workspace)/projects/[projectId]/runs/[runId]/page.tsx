import { ProjectRunDetailScreen } from "@/features/projects/components/project-run-detail-screen";

export default async function ProjectRunPage({
  params,
}: {
  params: Promise<{ projectId: string; runId: string }>;
}) {
  const { projectId, runId } = await params;
  return <ProjectRunDetailScreen projectId={projectId} runId={runId} />;
}
