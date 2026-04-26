import { ArrowLeft, ExternalLink } from "lucide-react";
import Link from "next/link";

import {
  Button,
  Card,
  CardBody,
  CardFooter,
  CardHeader,
  DescriptionItem,
  DescriptionList,
  InlineActions,
  Panel,
  Stack,
  StatusBadge,
  SurfaceNote,
} from "@ai-desk/ui";

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
      <InlineActions>
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
      </InlineActions>

      <Panel
        eyebrow="Project Audit"
        title={`${canvas.projectName} audit canvas`}
        actions={<StatusBadge label={canvas.confidence} tone="info" />}
      >
        <Stack gap="4">
          <p className="run-lead">{canvas.thesis}</p>
          <DescriptionList>
            <DescriptionItem label="Mode" value={canvas.auditMode} />
            <DescriptionItem label="Generated" value={formatGeneratedAt(canvas.generatedAt)} />
            <DescriptionItem label="Run" value={<code>{canvas.runId}</code>} />
          </DescriptionList>
        </Stack>
      </Panel>

      <section className="audit-canvas-grid" aria-label="Three pass audit canvas">
        {canvas.stages.map((stage) => (
          <Card key={stage.key}>
            <CardHeader>
              <div>
                <div className="ui-eyebrow">{stage.key.replaceAll("_", " ")}</div>
                <h3 className="list-card-title">{stage.title}</h3>
              </div>
              <StatusBadge
                label={stage.status.replaceAll("_", " ")}
                tone={stageTone(stage.status)}
              />
            </CardHeader>
            <CardBody>
              <Stack gap="3">
                <p className="ui-copy">{stage.summary}</p>
                <ul className="audit-stage-list">
                  {stage.findings.map((finding) => (
                    <li key={finding}>{finding}</li>
                  ))}
                </ul>
              </Stack>
            </CardBody>
            <CardFooter>
              <InlineActions>
                {stage.citations.map((citation) => (
                  <Link key={citation.href} href={citation.href}>
                    <Button tone="secondary">
                      {citation.label}
                      <ExternalLink className="button-icon" aria-hidden="true" />
                    </Button>
                  </Link>
                ))}
              </InlineActions>
            </CardFooter>
          </Card>
        ))}
      </section>

      <Panel eyebrow="Diff" title="What changed since the prior assessment">
        <Stack gap="3">
          {canvas.diffSummary.map((item) => (
            <SurfaceNote key={item} className="run-todo-row">
              <StatusBadge label="delta" tone="neutral" />
              <span>{item}</span>
            </SurfaceNote>
          ))}
        </Stack>
      </Panel>
    </div>
  );
}
