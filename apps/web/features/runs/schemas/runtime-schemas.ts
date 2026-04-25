import { type EventType, eventTypes } from "@ai-desk/contracts-runtime";

export type TimelineFilter = {
  type: EventType | "all";
  taskId: string;
  attemptId: string;
};

export const timelineFilterSchema = {
  parse(input: {
    type?: string | null;
    taskId?: string | null;
    attemptId?: string | null;
  }): TimelineFilter {
    const type =
      input.type && eventTypes.includes(input.type as EventType)
        ? (input.type as EventType)
        : "all";
    return {
      type,
      taskId: input.taskId ?? "",
      attemptId: input.attemptId ?? "",
    };
  },
};
