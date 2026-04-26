import { ArrowLeft, ExternalLink } from "lucide-react";
import Link from "next/link";

import { Button, Panel, StatusBadge } from "@ai-desk/ui";

import { getAuditCanvas } from "@/lib/demo-data/audit-data";

type BadgeTone = "neutral" | "success" | "warning" | "danger" | "info";

function formatGeneratedAt(value: string) {
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function stageTone(status: string): BadgeTone {
  if (status === "complete") {
    return "success";
  }
  if (status === "needs_review") {
    return "warning";
  }
  return "info";
}

export function AuditCanvasScreen({ projectId }: { projectId: string }) {
  const canvas = getAuditCanvas(projectId);

  return (
    <div className="page-stack">
      <div className="inline-actions">
        <Link href="/projects">
          <Button tone="secondary">
            <ArrowLeft className="button-icon" aria-hidden="true" />
            Projects
          </Button>
        </Link>
        <Link href={`/runs/${canvas.runId}/timeline`}>
          <Button tone="ghost">
            Runtime proof
            <ExternalLink className="button-icon" aria-hidden="true" />
          </Button>
        </Link>
      </div>

      <Panel
        eyebrow="Project Audit"
        title={`${canvas.projectName} audit canvas`}
        actions={<StatusBadge label={canvas.confidence} tone="info" />}
      >
        <div className="audit-hero">
          <p className="run-lead">{canvas.thesis}</p>
          <div className="signal-strip">
            <div className="signal-cell">
              <span>Mode</span>
              <strong>{canvas.auditMode}</strong>
            </div>
            <div className="signal-cell">
              <span>Generated</span>
              <strong>{formatGeneratedAt(canvas.generatedAt)}</strong>
            </div>
            <div className="signal-cell">
              <span>Run</span>
              <code>{canvas.runId}</code>
            </div>
          </div>
        </div>
      </Panel>

      <section className="audit-canvas-grid" aria-label="Three pass audit canvas">
        {canvas.stages.map((stage) => (
          <article key={stage.key} className="audit-stage-card">
            <div className="list-card-header">
              <div>
                <div className="ui-eyebrow">{stage.key.replaceAll("_", " ")}</div>
                <h3 className="list-card-title">{stage.title}</h3>
              </div>
              <StatusBadge
                label={stage.status.replaceAll("_", " ")}
                tone={stageTone(stage.status)}
              />
            </div>
            <p className="ui-copy">{stage.summary}</p>
            <ul className="audit-stage-list">
              {stage.findings.map((finding) => (
                <li key={finding}>{finding}</li>
              ))}
            </ul>
            <div className="inline-actions">
              {stage.citations.map((citation) => (
                <Link key={citation.href} href={citation.href}>
                  <Button tone="secondary">
                    {citation.label}
                    <ExternalLink className="button-icon" aria-hidden="true" />
                  </Button>
                </Link>
              ))}
            </div>
          </article>
        ))}
      </section>

      <Panel eyebrow="Diff" title="What changed since the prior assessment">
        <div className="list-grid">
          {canvas.diffSummary.map((item) => (
            <div key={item} className="run-todo-row">
              <StatusBadge label="delta" tone="neutral" />
              <span>{item}</span>
            </div>
          ))}
        </div>
      </Panel>
    </div>
  );
}
