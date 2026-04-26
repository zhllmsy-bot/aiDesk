import { createTranslator } from "next-intl";

import messages from "@/messages/review-en.json";

import type { ApprovalCenterCopy } from "./components/approval-center-screen";

export function getApprovalCenterCopy(): ApprovalCenterCopy {
  const t = createTranslator({
    locale: "en",
    messages,
    namespace: "review",
  });

  return {
    empty: t("empty"),
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
    runsDescription: t("runsDescription"),
    runsLabel: t("runsLabel"),
    searchLabel: t("searchLabel"),
    searchPlaceholder: t("searchPlaceholder"),
  };
}
