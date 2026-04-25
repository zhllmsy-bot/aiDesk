import type { CreateWorkspaceProjectInput } from "@ai-desk/contracts-projects";

type ValidationResult =
  | { success: true; data: CreateWorkspaceProjectInput }
  | { success: false; errors: Record<string, string> };

export function validateCreateProjectInput(input: CreateWorkspaceProjectInput): ValidationResult {
  const errors: Record<string, string> = {};
  const data = {
    name: input.name.trim(),
    root_path: input.root_path.trim(),
    default_branch: input.default_branch.trim() || "main",
    description: input.description?.trim() || null,
  };

  if (!data.name) {
    errors.name = "Name is required.";
  }
  if (!data.root_path.startsWith("/")) {
    errors.root_path = "Root path must be absolute.";
  }
  if (!data.default_branch) {
    errors.default_branch = "Default branch is required.";
  }

  return Object.keys(errors).length ? { success: false, errors } : { success: true, data };
}
