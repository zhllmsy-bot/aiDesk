import type { ArtifactRecord } from "@ai-desk/contracts-execution";

import { getApiErrorMessage, getApiHeaders, webApiClient } from "@/lib/api-client";
import { getArtifactFixture } from "@/lib/demo-data/artifact-data";

export async function getArtifact(artifactId: string): Promise<ArtifactRecord> {
  try {
    const { data, error, response } = await webApiClient.GET("/review/artifacts/{artifact_id}", {
      params: {
        path: {
          artifact_id: artifactId,
        },
      },
      headers: await getApiHeaders(),
    });
    if (!data) {
      throw new Error(getApiErrorMessage(error, response.status));
    }
    return data as unknown as ArtifactRecord;
  } catch {
    await new Promise((resolve) => setTimeout(resolve, 90));
    const artifact = getArtifactFixture(artifactId);
    if (!artifact) {
      throw new Error(`Artifact ${artifactId} not found`);
    }
    return artifact;
  }
}
