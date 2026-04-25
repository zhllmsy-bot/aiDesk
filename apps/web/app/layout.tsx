import type { Metadata } from "next";
import type { ReactNode } from "react";

import { AppProviders } from "./providers/app-providers";

import "./globals.css";

export const metadata: Metadata = {
  description: "ai-desk autonomous project control room",
  title: "ai-desk",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AppProviders>{children}</AppProviders>
      </body>
    </html>
  );
}
