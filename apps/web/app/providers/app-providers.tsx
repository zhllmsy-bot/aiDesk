"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { useState } from "react";

import { WorkspaceShell } from "@/components/layout/workspace-shell";

import { DevSessionBootstrap } from "./dev-session-bootstrap";

export function AppProviders({ children }: { children: ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            refetchOnWindowFocus: false,
            retry: 1,
            staleTime: 30_000,
          },
        },
      }),
  );

  return (
    <QueryClientProvider client={queryClient}>
      <DevSessionBootstrap />
      <WorkspaceShell>{children}</WorkspaceShell>
    </QueryClientProvider>
  );
}
