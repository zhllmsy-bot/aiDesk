import type { JsonObject } from "./tool";

export const providerKinds = ["chat", "agent_loop", "executor_harness"] as const;
export const capabilityFlags = [
  "streaming",
  "tool_calling",
  "structured_output",
  "vision",
  "computer_use",
  "subagents",
  "skills",
  "hooks",
] as const;

export type ProviderKind = (typeof providerKinds)[number];
export type CapabilityFlag = (typeof capabilityFlags)[number];

export interface ProviderCapabilities {
  provider: string;
  kind: ProviderKind;
  models: string[];
  flags: CapabilityFlag[];
  maxInputTokens?: number | null;
  maxOutputTokens?: number | null;
  metadata?: JsonObject;
}
