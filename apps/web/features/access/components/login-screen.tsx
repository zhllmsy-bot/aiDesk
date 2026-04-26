"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

import type { ProjectRole } from "@ai-desk/contracts-projects";

import { Button, Input, Panel, Select } from "@ai-desk/ui";

import { useAccessSession } from "../access-context";

const roleOptions: ProjectRole[] = ["admin", "maintainer", "reviewer", "viewer"];

export function LoginScreen() {
  const router = useRouter();
  const { signIn } = useAccessSession();
  const [isPending, startTransition] = useTransition();
  const [form, setForm] = useState({
    displayName: "Admin Operator",
    email: "admin@example.com",
    role: "admin" as ProjectRole,
  });

  return (
    <main className="login-shell">
      <section className="login-hero">
        <div className="ui-eyebrow">Run Control Access</div>
        <h1>Enter the AI run control room</h1>
        <p className="ui-copy">
          Sign in to reach project control, runtime monitoring, approval decisions, and evidence
          trails.
        </p>
      </section>

      <Panel eyebrow="Session" title="Sign in to workspace">
        <form
          className="form-grid"
          onSubmit={(event) => {
            event.preventDefault();
            startTransition(() => {
              signIn({
                displayName: form.displayName,
                email: form.email,
                role: form.role,
                activeProjectId: "proj_atlas",
              });
              router.push("/projects");
            });
          }}
        >
          <label className="field-stack" htmlFor="login-display-name">
            <span>Display name</span>
            <Input
              id="login-display-name"
              name="displayName"
              value={form.displayName}
              onChange={(event) =>
                setForm((current) => ({ ...current, displayName: event.target.value }))
              }
            />
          </label>

          <label className="field-stack" htmlFor="login-email">
            <span>Email</span>
            <Input
              id="login-email"
              name="email"
              type="email"
              value={form.email}
              onChange={(event) =>
                setForm((current) => ({ ...current, email: event.target.value }))
              }
            />
          </label>

          <label className="field-stack" htmlFor="login-role">
            <span>Role</span>
            <Select
              id="login-role"
              value={form.role}
              onChange={(event) =>
                setForm((current) => ({ ...current, role: event.target.value as ProjectRole }))
              }
            >
              {roleOptions.map((role) => (
                <option key={role} value={role}>
                  {role}
                </option>
              ))}
            </Select>
          </label>

          <div className="inline-actions">
            <Button type="submit" disabled={isPending}>
              {isPending ? "Signing in..." : "Enter workspace"}
            </Button>
          </div>
        </form>
      </Panel>
    </main>
  );
}
