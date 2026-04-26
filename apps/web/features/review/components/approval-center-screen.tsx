"use client";

import { useDeferredValue, useState } from "react";

import {
  ButtonLink,
  Card,
  CardBody,
  CardFooter,
  CardHeader,
  DescriptionList,
  EmptyState,
  InlineActions,
  KeyValue,
  Panel,
  SearchInput,
  SegmentedControl,
  Stack,
  StatCard,
  StatusBadge,
  SurfaceNote,
} from "@ai-desk/ui";

import { useApprovalsList } from "../hooks/use-approvals-list";
import { approvalListItemViewModel, approvalStatusLabel } from "../view-models";

export type ApprovalCenterCopy = {
  empty: string;
  filters: Record<"all" | "approved" | "expired" | "pending" | "rejected", string>;
  loading: string;
  metadata: {
    requester: string;
    requested: string;
    run: string;
    task: string;
  };
  openDetail: string;
  overviewCopy: string;
  overviewEyebrow: string;
  overviewTitle: string;
  pendingDescription: string;
  pendingLabel: string;
  queueEyebrow: string;
  queueTitle: string;
  runsDescription: string;
  runsLabel: string;
  searchLabel: string;
  searchPlaceholder: string;
};

export function ApprovalCenterScreen({ copy }: { copy: ApprovalCenterCopy }) {
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
  const statusOptions = ["all", "pending", "approved", "rejected", "expired"].map((value) => ({
    label: copy.filters[value as keyof ApprovalCenterCopy["filters"]],
    value,
  }));

  return (
    <div className="page-stack">
      <Panel eyebrow={copy.overviewEyebrow} title={copy.overviewTitle}>
        <div className="hero-grid">
          <div className="hero-copy">
            <p className="ui-copy">{copy.overviewCopy}</p>
            <InlineActions>
              <SearchInput
                aria-label={copy.searchLabel}
                onChange={(event) => setSearch(event.target.value)}
                onClear={() => setSearch("")}
                placeholder={copy.searchPlaceholder}
                value={search}
              />
              <SegmentedControl
                aria-label={copy.searchLabel}
                onValueChange={setStatusFilter}
                options={statusOptions}
                value={statusFilter}
              />
            </InlineActions>
          </div>
          <div className="hero-metrics">
            <StatCard
              description={copy.pendingDescription}
              label={copy.pendingLabel}
              value={pendingCount}
            />
            <StatCard
              description={copy.runsDescription}
              label={copy.runsLabel}
              value={new Set((data ?? []).map((item) => item.correlation.runId)).size}
            />
          </div>
        </div>
      </Panel>

      <Panel eyebrow={copy.queueEyebrow} title={copy.queueTitle}>
        {isLoading ? (
          <SurfaceNote>{copy.loading}</SurfaceNote>
        ) : items.length ? (
          <Stack gap="4">
            {items.map((approval) => (
              <Card key={approval.id}>
                <CardHeader>
                  <div>
                    <div className="ui-eyebrow">{approval.type}</div>
                    <h3 className="list-card-title">{approval.title}</h3>
                  </div>
                  <InlineActions>
                    <StatusBadge
                      label={approvalStatusLabel(approval.status)}
                      tone={approval.statusTone}
                    />
                    <StatusBadge label={approval.riskLevel} tone={approval.riskTone} />
                  </InlineActions>
                </CardHeader>
                <CardBody>
                  <Stack gap="3">
                    <p className="ui-copy">{approval.reason}</p>
                    <DescriptionList>
                      <KeyValue label={copy.metadata.requester} value={approval.requestedBy.name} />
                      <KeyValue label={copy.metadata.requested} value={approval.requestedAtLabel} />
                      <KeyValue label={copy.metadata.run} value={approval.correlation.runId} />
                      <KeyValue label={copy.metadata.task} value={approval.correlation.taskId} />
                    </DescriptionList>
                  </Stack>
                </CardBody>
                <CardFooter>
                  <ButtonLink href={approval.linkHref} variant="secondary">
                    {copy.openDetail}
                  </ButtonLink>
                </CardFooter>
              </Card>
            ))}
          </Stack>
        ) : (
          <EmptyState>{copy.empty}</EmptyState>
        )}
      </Panel>
    </div>
  );
}
