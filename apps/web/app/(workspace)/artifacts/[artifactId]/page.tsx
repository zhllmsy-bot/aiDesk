import { ArtifactDetailScreen } from "@/features/artifacts/components/artifact-detail-screen";

export default async function ArtifactDetailPage({
  params,
}: {
  params: Promise<{ artifactId: string }>;
}) {
  const { artifactId } = await params;
  return <ArtifactDetailScreen artifactId={artifactId} />;
}
