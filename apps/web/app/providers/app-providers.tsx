"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { useEffect, useState } from "react";

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
  const [DevSessionBootstrap, setDevSessionBootstrap] = useState<React.ComponentType | null>(null);

  useEffect(() => {
    if (process.env.NODE_ENV !== "development") {
      return;
    }

    let active = true;

    void import("./dev-session-bootstrap").then((mod) => {
      if (active) {
        setDevSessionBootstrap(() => mod.DevSessionBootstrap);
      }
    });

    return () => {
      active = false;
    };
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      {DevSessionBootstrap ? <DevSessionBootstrap /> : null}
      {children}
    </QueryClientProvider>
  );
}
