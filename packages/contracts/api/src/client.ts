import createClient from "openapi-fetch";

import type { components, operations, paths } from "./generated/schema.js";

export type ApiPaths = paths;
export type ApiOperations = operations;
export type ApiComponents = components;
export type ApiSchemas = components["schemas"];

export type ApiClientOptions = {
  baseUrl?: string;
  fetch?: typeof fetch;
  headers?: HeadersInit;
};

export function createApiClient(options: ApiClientOptions = {}) {
  return createClient<paths>(options);
}

export type ApiClient = ReturnType<typeof createApiClient>;
