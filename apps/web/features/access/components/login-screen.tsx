"use client";

import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

import type { ProjectRole } from "@ai-desk/contracts-projects";

import { Button, Input, Panel, Select } from "@ai-desk/ui";

import { useAccessSession } from "../access-context";

const roleOptions: ProjectRole[] = ["admin", "maintainer", "reviewer", "viewer"];

export function LoginScreen() {
  const router = useRouter();
  const t = useTranslations("access");
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
        <div className="ui-eyebrow">{t("eyebrow")}</div>
        <h1>{t("title")}</h1>
        <p className="ui-copy">{t("description")}</p>
      </section>

      <Panel eyebrow={t("sessionEyebrow")} title={t("sessionTitle")}>
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
            <span>{t("displayName")}</span>
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
            <span>{t("email")}</span>
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
            <span>{t("role")}</span>
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
              {isPending ? t("signingIn") : t("submit")}
            </Button>
          </div>
        </form>
      </Panel>
    </main>
  );
}
