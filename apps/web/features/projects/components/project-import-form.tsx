"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

import { Button, Input, Panel, Textarea } from "@ai-desk/ui";

import { useImportProject } from "../hooks/use-project-mutations";
import { validateCreateProjectInput } from "../schemas/project-forms";

export function ProjectImportForm() {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const mutation = useImportProject();
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [form, setForm] = useState({
    name: "",
    root_path: "",
    default_branch: "main",
    description: "",
  });

  return (
    <Panel eyebrow="Connect" title="Bring a project under control">
      <form
        className="form-grid"
        onSubmit={(event) => {
          event.preventDefault();

          const validation = validateCreateProjectInput(form);
          if (!validation.success) {
            setErrors(validation.errors);
            return;
          }

          setErrors({});

          startTransition(async () => {
            try {
              const response = await mutation.mutateAsync(validation.data);
              router.push(`/projects/${response.item.project.id}`);
            } catch (error) {
              setErrors({
                form: error instanceof Error ? error.message : "Import failed",
              });
            }
          });
        }}
      >
        <label className="field-stack" htmlFor="project-import-name">
          <span>Name</span>
          <Input
            id="project-import-name"
            value={form.name}
            onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
            placeholder="Atlas Control Plane"
          />
          {errors.name ? <span className="field-error">{errors.name}</span> : null}
        </label>

        <label className="field-stack" htmlFor="project-import-root-path">
          <span>Root path</span>
          <Input
            id="project-import-root-path"
            value={form.root_path}
            onChange={(event) =>
              setForm((current) => ({ ...current, root_path: event.target.value }))
            }
            placeholder="/Users/admin/Desktop/ai-desk"
          />
          {errors.root_path ? <span className="field-error">{errors.root_path}</span> : null}
        </label>

        <label className="field-stack" htmlFor="project-import-default-branch">
          <span>Default branch</span>
          <Input
            id="project-import-default-branch"
            value={form.default_branch}
            onChange={(event) =>
              setForm((current) => ({ ...current, default_branch: event.target.value }))
            }
          />
          {errors.default_branch ? (
            <span className="field-error">{errors.default_branch}</span>
          ) : null}
        </label>

        <label className="field-stack" htmlFor="project-import-description">
          <span>Description</span>
          <Textarea
            id="project-import-description"
            value={form.description}
            onChange={(event) =>
              setForm((current) => ({ ...current, description: event.target.value }))
            }
            placeholder="Optional project context"
          />
        </label>

        {errors.form ? <div className="field-error">{errors.form}</div> : null}

        <div className="inline-actions">
          <Button type="submit" disabled={isPending || mutation.isPending}>
            {isPending || mutation.isPending ? "Connecting..." : "Connect project"}
          </Button>
        </div>
      </form>
    </Panel>
  );
}
