import { describe, expect, it } from "vitest";

import { withClientTraceHeaders } from "@/lib/api-client";

describe("api client trace headers", () => {
  it("adds W3C trace headers for browser-originated requests", () => {
    const headers = withClientTraceHeaders();

    expect(headers.get("X-Trace-ID")).toBeTruthy();
    expect(headers.get("traceparent")).toMatch(/^00-[0-9a-f]{32}-[0-9a-f]{16}-01$/);
  });

  it("preserves an existing traceparent", () => {
    const traceparent = "00-0123456789abcdef0123456789abcdef-0123456789abcdef-01";
    const headers = withClientTraceHeaders({ traceparent });

    expect(headers.get("traceparent")).toBe(traceparent);
  });
});
