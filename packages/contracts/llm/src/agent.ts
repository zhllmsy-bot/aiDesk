import type { ChatMessage } from "./chat";
import type { ProviderCapabilities } from "./provider";
import type { JsonObject, ToolCall, ToolResult } from "./tool";

export const agentEventTypes = [
  "session.started",
  "message.delta",
  "message.completed",
  "tool.requested",
  "tool.completed",
  "skill.injected",
  "hook.completed",
  "session.completed",
  "session.failed",
] as const;

export type AgentEventType = (typeof agentEventTypes)[number];

export interface AgentBudget {
  maxTokens?: number | null;
  maxToolCalls?: number | null;
  maxWallClockSeconds?: number | null;
  maxCostUsd?: number | null;
}

export interface AgentProfile {
  id: string;
  prompt: string;
  toolAllowlist: string[];
  model: string;
  budget: AgentBudget;
  skills?: string[];
  hooks?: string[];
  metadata?: JsonObject;
}

export interface AgentLoopRequest {
  sessionId: string;
  profile: AgentProfile;
  messages: ChatMessage[];
  contextLedgerId?: string | null;
  capabilities?: ProviderCapabilities;
  metadata?: JsonObject;
}

export interface AgentEvent {
  id: string;
  sessionId: string;
  type: AgentEventType;
  sequence: number;
  occurredAt: string;
  message?: ChatMessage | null;
  toolCall?: ToolCall | null;
  toolResult?: ToolResult | null;
  summary?: string | null;
  metadata?: JsonObject;
}
