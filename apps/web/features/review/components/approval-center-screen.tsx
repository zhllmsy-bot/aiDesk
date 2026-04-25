"use client";

import Link from "next/link";
import type { ChangeEvent } from "react";
import { useDeferredValue, useState } from "react";

import { Button, Input, Panel, Stack, StatusBadge } from "@ai-desk/ui";

import { useApprovalsList } from "../hooks/use-approvals-list";
import { approvalListItemViewModel, approvalStatusLabel } from "../view-models";

export function ApprovalCenterScreen() {
  const { data, isLoading } = useApprovalsList();
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const deferredSearch = useDeferredValue(search);

  const items = (data ?? []).map(approvalListItemViewModel).filter((approval) => {
    const matchesStatus = statusFilter === "all" || approval.status === statusFilter;
    const query = deferredSearch.trim().toLowerCase();
    const matchesSearch =
      !query ||
      approval.title.toLowerCase().includes(query) ||
      approval.correlation.runId.toLowerCase().includes(query) ||
      approval.requestedBy.name.toLowerCase().includes(query);

    return matchesStatus && matchesSearch;
  });

  const pendingCount = (data ?? []).filter((approval) => approval.status === "pending").length;

  return (
    <div className="page-stack">
      <Panel eyebrow="Approval Center" title="Operator decisions with provenance">
        <div className="hero-grid">
          <div className="hero-copy">
            <p className="ui-copy">
              Every decision keeps the request intent, run correlation, and linked artifacts in the
              same place so the operator can approve scope without losing runtime context.
            </p>
            <div className="inline-actions">
              <Input
                aria-label="Search approvals"
                value={search}
                onChange={(event: ChangeEvent<HTMLInputElement>) => setSearch(event.target.value)}
                placeholder="Search by title, run, or requester"
              />
              <div className="inline-actions">
                {["all", "pending", "approved", "rejected", "expired"].map((value) => (
                  <Button
                    key={value}
                    tone={statusFilter === value ? "primary" : "secondary"}
                    onClick={() => setStatusFilter(value)}
                  >
                    {value}
                  </Button>
                ))}
              </div>
            </div>
          </div>
          <div className="hero-metrics">
            <div className="metric-card">
              <span className="ui-eyebrow">Pending queue</span>
              <strong>{pendingCount}</strong>
              <p className="ui-copy">Requests that still need an operator decision.</p>
            </div>
            <div className="metric-card">
              <span className="ui-eyebrow">Correlated runs</span>
              <strong>{new Set((data ?? []).map((item) => item.correlation.runId)).size}</strong>
              <p className="ui-copy">Every item links back to run and task context.</p>
            </div>
          </div>
        </div>
      </Panel>

      <Panel eyebrow="Queue" title="Approvals">
        {isLoading ? (
          <div className="surface-note">Loading approval queue...</div>
        ) : items.length ? (
          <div className="list-grid">
            {items.map((approval) => (
              <article key={approval.id} className="list-card">
                <div className="list-card-header">
                  <div>
                    <div className="ui-eyebrow">{approval.type}</div>
                    <h3 style={{ margin: 0 }}>{approval.title}</h3>
                  </div>
                  <div className="inline-actions">
                    <StatusBadge
                      label={approvalStatusLabel(approval.status)}
                      tone={approval.statusTone}
                    />
                    <StatusBadge label={approval.riskLevel} tone={approval.riskTone} />
                  </div>
                </div>
                <p className="ui-copy">{approval.reason}</p>
                <div className="meta-row">
                  <span>Requester: {approval.requestedBy.name}</span>
                  <span>Requested: {approval.requestedAtLabel}</span>
                  <span>Run: {approval.correlation.runId}</span>
                  <span>Task: {approval.correlation.taskId}</span>
                </div>
                <Stack gap="var(--space-3)">
                  <Link href={approval.linkHref}>
                    <Button>Open detail</Button>
                  </Link>
                </Stack>
              </article>
            ))}
          </div>
        ) : (
          <div className="empty-state">No approvals match the current filters.</div>
        )}
      </Panel>
    </div>
  );
}
