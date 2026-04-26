import { getTranslations } from "next-intl/server";

import type { ApprovalCenterCopy } from "./components/approval-center-screen";
import type { ApprovalDetailCopy } from "./components/approval-detail-screen";

export async function getApprovalCenterCopy(): Promise<ApprovalCenterCopy> {
  const t = await getTranslations("review");

  return {
    approve: t("approve"),
    empty: t("empty"),
    filterLabel: t("filterLabel"),
    filters: {
      all: t("filters.all"),
      approved: t("filters.approved"),
      expired: t("filters.expired"),
      pending: t("filters.pending"),
      rejected: t("filters.rejected"),
    },
    loading: t("loading"),
    metadata: {
      requester: t("metadata.requester"),
      requested: t("metadata.requested"),
      run: t("metadata.run"),
      task: t("metadata.task"),
    },
    openDetail: t("openDetail"),
    overviewCopy: t("overviewCopy"),
    overviewEyebrow: t("overviewEyebrow"),
    overviewTitle: t("overviewTitle"),
    pendingDescription: t("pendingDescription"),
    pendingLabel: t("pendingLabel"),
    queueEyebrow: t("queueEyebrow"),
    queueTitle: t("queueTitle"),
    reject: t("reject"),
    runsDescription: t("runsDescription"),
    runsLabel: t("runsLabel"),
    searchLabel: t("searchLabel"),
    searchPlaceholder: t("searchPlaceholder"),
  };
}

export async function getApprovalDetailCopy(): Promise<ApprovalDetailCopy> {
  const t = await getTranslations("review.detail");

  return {
    approve: t("approve"),
    approveSuccess: t("approveSuccess"),
    backToQueue: t("backToQueue"),
    decisionEyebrow: t("decisionEyebrow"),
    decisionTitle: t("decisionTitle"),
    evidenceEyebrow: t("evidenceEyebrow"),
    evidenceTitle: t("evidenceTitle"),
    loading: t("loading"),
    metadata: {
      attempt: t("metadata.attempt"),
      project: t("metadata.project"),
      requested: t("metadata.requested"),
      requester: t("metadata.requester"),
      run: t("metadata.run"),
      task: t("metadata.task"),
    },
    noteLabel: t("noteLabel"),
    notePlaceholder: t("notePlaceholder"),
    openArtifact: t("openArtifact"),
    openAttempt: t("openAttempt"),
    openRuntime: t("openRuntime"),
    reject: t("reject"),
    rejectSuccess: t("rejectSuccess"),
    resolutionNote: t("resolutionNote"),
    resolvedState: t("resolvedState"),
    reviewEyebrow: t("reviewEyebrow"),
    unavailable: t("unavailable"),
  };
}
