"use client";

import { ArrowLeft, ExternalLink } from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";

import {
  Button,
  Card,
  CardBody,
  CardFooter,
  CardHeader,
  DescriptionItem,
  DescriptionList,
  EmptyState,
  InlineActions,
  Panel,
  Stack,
  StatusBadge,
  SurfaceNote,
  Textarea,
} from "@ai-desk/ui";

import { useApprovalDetail } from "../hooks/use-approval-detail";
import { useResolveApproval } from "../hooks/use-resolve-approval";
import { approvalStatusLabel } from "../view-models";

type BadgeTone = "neutral" | "success" | "warning" | "danger" | "info";

export type ApprovalDetailCopy = {
  approve: string;
  approveSuccess: string;
  backToQueue: string;
  decisionEyebrow: string;
  decisionTitle: string;
  evidenceEyebrow: string;
  evidenceTitle: string;
  loading: string;
  metadata: {
    attempt: string;
    project: string;
    requested: string;
    requester: string;
    run: string;
    task: string;
  };
  noteLabel: string;
  notePlaceholder: string;
  openArtifact: string;
  openAttempt: string;
  openRuntime: string;
  reject: string;
  rejectSuccess: string;
  resolutionNote: string;
  resolvedState: string;
  reviewEyebrow: string;
  unavailable: string;
};

function formatRequestedAt(value: string) {
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function riskTone(riskLevel: string): BadgeTone {
  if (riskLevel === "critical" || riskLevel === "high") {
    return "danger";
  }
  if (riskLevel === "medium") {
    return "warning";
  }
  return "info";
}

function statusTone(status: string): BadgeTone {
  if (status === "approved") {
    return "success";
  }
  if (status === "rejected" || status === "expired" || status === "cancelled") {
    return "danger";
  }
  return "warning";
}

export function ApprovalDetailScreen({
  approvalId,
  copy,
}: {
  approvalId: string;
  copy: ApprovalDetailCopy;
}) {
  const detailQuery = useApprovalDetail(approvalId);
  const resolveMutation = useResolveApproval();
  const [note, setNote] = useState("");
  const approval = resolveMutation.data ?? detailQuery.data ?? null;
  const activeResolution = resolveMutation.variables?.status ?? null;

  const successMessage = useMemo(() => {
    if (approval?.status === "approved") {
      return copy.approveSuccess;
    }
    if (approval?.status === "rejected") {
      return copy.rejectSuccess;
    }
    return null;
  }, [approval?.status, copy.approveSuccess, copy.rejectSuccess]);

  function handleResolve(status: "approved" | "rejected") {
    resolveMutation.mutate({
      approvalId,
      status,
      reason: note.trim() || (status === "approved" ? copy.approveSuccess : copy.rejectSuccess),
    });
  }

  if (detailQuery.isLoading && !approval) {
    return <SurfaceNote>{copy.loading}</SurfaceNote>;
  }

  if (!approval) {
    return (
      <div className="page-stack">
        <EmptyState>{copy.unavailable}</EmptyState>
      </div>
    );
  }

  const isPending = approval.status === "pending";

  return (
    <div className="page-stack">
      <InlineActions>
        <Link href="/review">
          <Button tone="secondary">
            <ArrowLeft className="button-icon" aria-hidden="true" />
            {copy.backToQueue}
          </Button>
        </Link>
        <Link href={`/runs/${approval.correlation.runId}/timeline`}>
          <Button tone="ghost">
            {copy.openRuntime}
            <ExternalLink className="button-icon" aria-hidden="true" />
          </Button>
        </Link>
        <Link href={`/ops/attempts/${approval.correlation.attemptId}`}>
          <Button tone="ghost">
            {copy.openAttempt}
            <ExternalLink className="button-icon" aria-hidden="true" />
          </Button>
        </Link>
      </InlineActions>

      <Panel
        eyebrow={copy.reviewEyebrow}
        title={approval.title}
        actions={
          <InlineActions>
            <StatusBadge
              label={approvalStatusLabel(approval.status)}
              tone={statusTone(approval.status)}
            />
            <StatusBadge label={approval.riskLevel} tone={riskTone(approval.riskLevel)} />
          </InlineActions>
        }
      >
        <div className="hero-grid">
          <div className="hero-copy">
            <p className="run-lead">{approval.reason}</p>
            <DescriptionList>
              <DescriptionItem
                label={copy.metadata.requested}
                value={formatRequestedAt(approval.requestedAt)}
              />
              <DescriptionItem label={copy.metadata.requester} value={approval.requestedBy.name} />
              <DescriptionItem
                label={copy.metadata.project}
                value={approval.correlation.projectId}
              />
            </DescriptionList>
          </div>
          <div className="hero-metrics">
            <SurfaceNote>
              <strong>{copy.metadata.run}</strong>
              <span>{approval.correlation.runId}</span>
            </SurfaceNote>
            <SurfaceNote>
              <strong>{copy.metadata.task}</strong>
              <span>{approval.correlation.taskId}</span>
            </SurfaceNote>
            <SurfaceNote>
              <strong>{copy.metadata.attempt}</strong>
              <span>{approval.correlation.attemptId}</span>
            </SurfaceNote>
          </div>
        </div>
      </Panel>

      <div className="split-grid">
        <Card>
          <CardHeader>
            <div>
              <div className="ui-eyebrow">{copy.decisionEyebrow}</div>
              <h2 className="list-card-title">{copy.decisionTitle}</h2>
            </div>
          </CardHeader>
          <CardBody>
            <Stack gap="4">
              {isPending ? (
                <>
                  <Textarea
                    aria-label={copy.noteLabel}
                    onChange={(event) => setNote(event.target.value)}
                    placeholder={copy.notePlaceholder}
                    value={note}
                  />
                  {resolveMutation.error ? (
                    <SurfaceNote>{resolveMutation.error.message}</SurfaceNote>
                  ) : null}
                  <InlineActions>
                    <Button
                      disabled={resolveMutation.isPending}
                      onClick={() => handleResolve("approved")}
                    >
                      {resolveMutation.isPending && activeResolution === "approved"
                        ? `${copy.approve}...`
                        : copy.approve}
                    </Button>
                    <Button
                      tone="destructive"
                      disabled={resolveMutation.isPending}
                      onClick={() => handleResolve("rejected")}
                    >
                      {resolveMutation.isPending && activeResolution === "rejected"
                        ? `${copy.reject}...`
                        : copy.reject}
                    </Button>
                  </InlineActions>
                </>
              ) : (
                <SurfaceNote>
                  <strong>{copy.resolvedState}</strong>
                  <span>{approvalStatusLabel(approval.status)}</span>
                </SurfaceNote>
              )}
              {approval.resolutionNote ? (
                <DescriptionList>
                  <DescriptionItem label={copy.resolutionNote} value={approval.resolutionNote} />
                </DescriptionList>
              ) : null}
              {successMessage && !isPending ? <SurfaceNote>{successMessage}</SurfaceNote> : null}
            </Stack>
          </CardBody>
        </Card>

        <Card>
          <CardHeader>
            <div>
              <div className="ui-eyebrow">{copy.evidenceEyebrow}</div>
              <h2 className="list-card-title">{copy.evidenceTitle}</h2>
            </div>
          </CardHeader>
          <CardBody>
            <Stack gap="3">
              <DescriptionList>
                <DescriptionItem label={copy.metadata.run} value={approval.correlation.runId} />
                <DescriptionItem label={copy.metadata.task} value={approval.correlation.taskId} />
                <DescriptionItem
                  label={copy.metadata.attempt}
                  value={approval.correlation.attemptId}
                />
              </DescriptionList>
              {approval.relatedArtifacts?.length ? (
                <Stack gap="2">
                  {approval.relatedArtifacts.map((artifactId) => (
                    <Link href={`/artifacts/${artifactId}`} key={artifactId}>
                      <Button tone="secondary">
                        {copy.openArtifact}
                        <ExternalLink className="button-icon" aria-hidden="true" />
                      </Button>
                    </Link>
                  ))}
                </Stack>
              ) : (
                <SurfaceNote>{copy.unavailable}</SurfaceNote>
              )}
            </Stack>
          </CardBody>
          <CardFooter>
            <Link href={`/projects/${approval.correlation.projectId}/audit`}>
              <Button tone="ghost">
                {approval.correlation.projectId}
                <ExternalLink className="button-icon" aria-hidden="true" />
              </Button>
            </Link>
          </CardFooter>
        </Card>
      </div>
    </div>
  );
}
