import type { ArtifactRecord } from "@ai-desk/contracts-execution";

import { getApiErrorMessage, getApiHeaders, webApiClient } from "@/lib/api-client";
import { listArtifactFixtures } from "@/lib/demo-data/artifact-data";

export async function listArtifacts(): Promise<ArtifactRecord[]> {
  try {
    const { data, error, response } = await webApiClient.GET("/review/artifacts", {
      headers: await getApiHeaders(),
    });
    if (!data) {
      throw new Error(getApiErrorMessage(error, response.status));
    }
    return data.items as unknown as ArtifactRecord[];
  } catch {
    await new Promise((resolve) => setTimeout(resolve, 120));
    return listArtifactFixtures();
  }
}
