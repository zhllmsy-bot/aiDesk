"use client";

import dynamic from "next/dynamic";

import { SurfaceNote } from "@ai-desk/ui";

import type { ApprovalDetailCopy } from "./approval-detail-screen";

const ApprovalDetailScreen = dynamic(
  () => import("./approval-detail-screen").then((module) => module.ApprovalDetailScreen),
  {
    loading: () => <SurfaceNote>Loading approval detail...</SurfaceNote>,
    ssr: false,
  },
);

export function ApprovalDetailShell({
  approvalId,
  copy,
}: {
  approvalId: string;
  copy: ApprovalDetailCopy;
}) {
  return <ApprovalDetailScreen approvalId={approvalId} copy={copy} />;
}
