export type JsonPrimitive = string | number | boolean | null;
export type JsonValue = JsonPrimitive | JsonObject | JsonValue[];
export interface JsonObject {
  [key: string]: JsonValue;
}

export const toolCallStatuses = ["pending", "running", "succeeded", "failed"] as const;

export type ToolCallStatus = (typeof toolCallStatuses)[number];

export interface ToolDefinition {
  name: string;
  description?: string;
  parameters: JsonObject;
  strict?: boolean;
  providerPayload?: JsonObject;
}

export interface ToolCall {
  id: string;
  name: string;
  arguments: JsonObject;
  status?: ToolCallStatus;
  providerPayload?: JsonObject;
}

export interface ToolResult {
  toolCallId: string;
  name: string;
  status: Exclude<ToolCallStatus, "pending" | "running">;
  content: string | JsonValue;
  error?: string | null;
  providerPayload?: JsonObject;
}
