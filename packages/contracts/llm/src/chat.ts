import type { JsonObject } from "./tool";
import type { ToolCall, ToolDefinition, ToolResult } from "./tool";

export const llmContractVersion = "2026-04-25.llm.v1" as const;

export const chatRoles = ["system", "user", "assistant", "tool"] as const;
export const streamChunkTypes = ["message_start", "delta", "tool_call", "done", "error"] as const;

export type ChatRole = (typeof chatRoles)[number];
export type StreamChunkType = (typeof streamChunkTypes)[number];

export interface ChatMessage {
  role: ChatRole;
  content: string;
  name?: string | null;
  toolCallId?: string | null;
  toolCalls?: ToolCall[];
  providerPayload?: JsonObject;
}

export interface ChatRequest {
  schemaVersion: typeof llmContractVersion;
  provider?: string | null;
  model: string;
  messages: ChatMessage[];
  tools?: ToolDefinition[];
  toolResults?: ToolResult[];
  temperature?: number | null;
  maxTokens?: number | null;
  stream?: boolean;
  metadata?: JsonObject;
}

export interface StreamChunk {
  schemaVersion: typeof llmContractVersion;
  id: string;
  type: StreamChunkType;
  delta?: string | null;
  toolCall?: ToolCall | null;
  error?: string | null;
  providerPayload?: JsonObject;
}

export interface ChatResponse {
  schemaVersion: typeof llmContractVersion;
  id: string;
  provider: string;
  model: string;
  message: ChatMessage;
  toolCalls: ToolCall[];
  finishReason?: string | null;
  usage?: {
    inputTokens?: number;
    outputTokens?: number;
    totalTokens?: number;
  };
  providerPayload?: JsonObject;
}
