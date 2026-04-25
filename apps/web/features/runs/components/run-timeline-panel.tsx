"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { startTransition, useEffect, useState } from "react";

import { eventTypes } from "@ai-desk/contracts-runtime";
import { Button, CodeBlock, Panel, StatusBadge } from "@ai-desk/ui";

import { timelineItemViewModel } from "@/lib/view-models/runtime-view-models";
import { useRunEvents } from "../hooks/use-run-events";
import { timelineFilterSchema } from "../schemas/runtime-schemas";
import { RunFilterBar } from "./run-filter-bar";

export function RunTimelinePanel({
  runId,
  projectId,
}: {
  runId: string;
  projectId: string;
}) {
  const { data, isLoading } = useRunEvents(runId);
  const searchParams = useSearchParams();
  const pathname = usePathname();
  const router = useRouter();
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null);

  const parsedFilter = timelineFilterSchema.parse({
    type: searchParams.get("type") ?? "all",
    taskId: searchParams.get("taskId") ?? "",
    attemptId: searchParams.get("attemptId") ?? "",
  });

  useEffect(() => {
    if (!selectedEventId && data?.length) {
      setSelectedEventId(data.at(-1)?.eventId ?? null);
    }
  }, [data, selectedEventId]);

  const items = (data ?? []).map(timelineItemViewModel).filter((event) => {
    if (parsedFilter.type !== "all" && event.eventType !== parsedFilter.type) {
      return false;
    }

    if (parsedFilter.taskId && event.correlation.taskId !== parsedFilter.taskId) {
      return false;
    }

    if (parsedFilter.attemptId && event.correlation.attemptId !== parsedFilter.attemptId) {
      return false;
    }

    return true;
  });

  const selected = items.find((item) => item.eventId === selectedEventId) ?? items.at(-1) ?? null;

  function updateSearchParams(next: {
    type: string;
    taskId: string;
    attemptId: string;
  }) {
    const params = new URLSearchParams(searchParams.toString());
    if (next.type && next.type !== "all") {
      params.set("type", next.type);
    } else {
      params.delete("type");
    }

    if (next.taskId.trim()) {
      params.set("taskId", next.taskId.trim());
    } else {
      params.delete("taskId");
    }

    if (next.attemptId.trim()) {
      params.set("attemptId", next.attemptId.trim());
    } else {
      params.delete("attemptId");
    }

    startTransition(() => {
      const query = params.toString();
      router.replace(query ? `${pathname}?${query}` : pathname);
    });
  }

  return (
    <div className="runtime-section-grid">
      <Panel eyebrow="Event log" title="Runtime history">
        <div className="runtime-panel-stack">
          <p className="ui-copy">
            Filter by event, task, or attempt; the selected event exposes the payload that explains
            why the run changed state.
          </p>
          <RunFilterBar
            filter={{
              type: parsedFilter.type,
              taskId: parsedFilter.taskId ?? "",
              attemptId: parsedFilter.attemptId ?? "",
            }}
            eventTypes={eventTypes}
            onChange={updateSearchParams}
          />

          {isLoading ? (
            <div className="surface-note">Loading runtime history...</div>
          ) : (
            <div className="timeline-shell">
              <ul className="timeline-scroll" aria-label="Run timeline events">
                {items.map((event) => (
                  <li key={event.eventId}>
                    <button
                      className={`timeline-entry-button${selected?.eventId === event.eventId ? " timeline-entry-active" : ""}`}
                      onClick={() => setSelectedEventId(event.eventId)}
                      type="button"
                    >
                      <div className="timeline-entry-meta">
                        <StatusBadge label={event.label} tone={event.statusTone} />
                        <span>{event.occurredAtLabel}</span>
                      </div>
                      <strong>{event.summary}</strong>
                      <div className="meta-row">
                        <span>trace: {event.correlation.traceId}</span>
                        {event.correlation.taskId ? (
                          <span>task: {event.correlation.taskId}</span>
                        ) : null}
                        {event.correlation.attemptId ? (
                          <span>attempt: {event.correlation.attemptId}</span>
                        ) : null}
                      </div>
                    </button>
                  </li>
                ))}
              </ul>

              <div className="timeline-detail">
                {selected ? (
                  <>
                    <div className="timeline-detail-header">
                      <div>
                        <div className="ui-eyebrow">Event payload</div>
                        <h3>{selected.label}</h3>
                      </div>
                      <div className="inline-actions">
                        <Link
                          href={`/runs/${runId}/telemetry#trace-${selected.correlation.traceId}`}
                        >
                          <Button tone="secondary">Open telemetry</Button>
                        </Link>
                        {selected.correlation.attemptId ? (
                          <Link href={`/ops/attempts/${selected.correlation.attemptId}`}>
                            <Button tone="ghost">Ops panel</Button>
                          </Link>
                        ) : null}
                        {selected.correlation.taskId ? (
                          <Link
                            href={`/projects/${projectId}/runs/${runId}?taskId=${selected.correlation.taskId}`}
                          >
                            <Button tone="ghost">Project run</Button>
                          </Link>
                        ) : null}
                      </div>
                    </div>
                    <p className="ui-copy">{selected.summary}</p>
                    <CodeBlock code={selected.detailCode} language="json" />
                  </>
                ) : (
                  <div className="empty-state">No runtime events match the current filters.</div>
                )}
              </div>
            </div>
          )}
        </div>
      </Panel>
    </div>
  );
}
