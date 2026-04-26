"use client";

import dynamic from "next/dynamic";

import { SurfaceNote } from "@ai-desk/ui";

import type { ApprovalCenterCopy } from "./approval-center-screen";

const ApprovalCenterScreen = dynamic(
  () => import("./approval-center-screen").then((module) => module.ApprovalCenterScreen),
  {
    loading: () => <SurfaceNote>Loading approval queue...</SurfaceNote>,
    ssr: false,
  },
);

export function ApprovalCenterShell({ copy }: { copy: ApprovalCenterCopy }) {
  return <ApprovalCenterScreen copy={copy} />;
}
