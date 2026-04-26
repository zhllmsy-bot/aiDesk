export const projectRoutes = {
  index: () => "/projects",
  detail: ({ projectId }: { projectId: string }) => `/projects/${projectId}`,
  audit: ({ projectId }: { projectId: string }) => `/projects/${projectId}/audit`,
  iteration: ({ projectId, iterationId }: { projectId: string; iterationId: string }) =>
    `/projects/${projectId}/iterations/${iterationId}`,
  run: ({ projectId, runId }: { projectId: string; runId: string }) =>
    `/projects/${projectId}/runs/${runId}`,
};
