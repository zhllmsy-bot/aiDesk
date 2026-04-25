"use client";

import { useId } from "react";

import type { EventType } from "@ai-desk/contracts-runtime";
import { Input, Select } from "@ai-desk/ui";

type FilterState = {
  type: "all" | EventType;
  taskId: string;
  attemptId: string;
};

export function RunFilterBar({
  filter,
  eventTypes,
  onChange,
}: {
  filter: FilterState;
  eventTypes: readonly EventType[];
  onChange: (next: FilterState) => void;
}) {
  const typeId = useId();
  const taskId = useId();
  const attemptId = useId();

  return (
    <div className="runtime-filter-bar">
      <label className="runtime-field" htmlFor={typeId}>
        <span className="runtime-field-label">Event type</span>
        <Select
          id={typeId}
          value={filter.type}
          onChange={(event) =>
            onChange({
              ...filter,
              type: event.target.value as FilterState["type"],
            })
          }
        >
          <option value="all">all events</option>
          {eventTypes.map((eventType) => (
            <option key={eventType} value={eventType}>
              {eventType}
            </option>
          ))}
        </Select>
      </label>

      <label className="runtime-field" htmlFor={taskId}>
        <span className="runtime-field-label">Task id</span>
        <Input
          id={taskId}
          value={filter.taskId}
          onChange={(event) => onChange({ ...filter, taskId: event.target.value })}
          placeholder="loop-1-execution"
        />
      </label>

      <label className="runtime-field" htmlFor={attemptId}>
        <span className="runtime-field-label">Attempt id</span>
        <Input
          id={attemptId}
          value={filter.attemptId}
          onChange={(event) => onChange({ ...filter, attemptId: event.target.value })}
          placeholder="attempt id"
        />
      </label>
    </div>
  );
}
